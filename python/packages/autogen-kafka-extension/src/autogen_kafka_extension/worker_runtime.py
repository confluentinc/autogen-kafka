import asyncio
import inspect
import logging
import uuid
import warnings
from asyncio import Task, Future
from typing import Dict, Callable, Awaitable, cast, TypeVar, Any, Sequence, Mapping, Set, Type, List

from autogen_core import (
    AgentRuntime, Agent, AgentId, AgentInstantiationContext, Subscription, TopicId, CancellationToken,
    JSON_DATA_CONTENT_TYPE, MessageContext, MessageHandlerContext, AgentType, AgentMetadata, MessageSerializer,
)
from autogen_core._runtime_impl_helpers import SubscriptionManager
from autogen_core._serialization import SerializationRegistry
from autogen_core._single_threaded_agent_runtime import type_func_alias
from autogen_core._telemetry import TraceHelper, MessageRuntimeTracingConfig, get_telemetry_grpc_metadata
from cloudevents.pydantic import CloudEvent
from kstreams import create_engine, ConsumerRecord, Stream, Send, middleware, StreamEngine
from kstreams.backends import Kafka
from opentelemetry.trace import TracerProvider

from autogen_kafka_extension import _constants
from autogen_kafka_extension._agent_registry import AgentRegistry
from autogen_kafka_extension._message import Message, MessageType
from autogen_kafka_extension._topic_admin import TopicAdmin
from autogen_kafka_extension.worker_config import WorkerConfig
from autogen_kafka_extension._message_serdes import EventDeserializer, EventSerializer

T = TypeVar("T", bound=Agent)
logger = logging.getLogger(__name__)

# Helper function to raise exceptions from background tasks
def _raise_on_exception(task: Task[Any]) -> None:
    exception = task.exception()
    if exception is not None:
        raise exception

class KafkaWorkerAgentRuntime(AgentRuntime):
    """
    A Kafka worker agent runtime that processes messages from Kafka topics.
    Extends AgentRuntime to provide Kafka-specific functionality for consuming
    and processing messages from configured Kafka topics.
    """

    def __init__(
        self,
        config: WorkerConfig,
        tracer_provider: TracerProvider | None = None
    ) -> None:
        """
        Initialize a new KafkaWorkerAgentRuntime instance.

        Args:
            config: Configuration settings for the Kafka worker.
            tracer_provider: Optional OpenTelemetry tracer provider for distributed tracing.

        Sets up agent management, subscription management, serialization, and async task tracking.
        """
        super().__init__()
        # Initialize tracing
        self._trace_helper = TraceHelper(tracer_provider, MessageRuntimeTracingConfig("Worker Runtime"))

        # Runtime state
        self._started: bool = False
        self._config = config
        self._stream_engine: StreamEngine | None = None

        # Agent management
        self._agent_factories: Dict[
            str, Callable[[], Agent | Awaitable[Agent]] | Callable[[AgentRuntime, AgentId], Agent | Awaitable[Agent]]
        ] = {}
        self._instantiated_agents: Dict[AgentId, Agent] = {}
        self._agent_instance_types: Dict[str, Type[Agent]] = {}

        # Core services
        self._subscription_manager = SubscriptionManager()
        self._serialization_registry = SerializationRegistry()

        # Async task management
        self._background_tasks: Set[Task[Any]] = set()
        self._pending_requests: Dict[str, Future[Any]] = {}
        self._pending_requests_lock = asyncio.Lock()
        self._next_request_id = 0

        # self._agent_registry = AgentRegistry(config)

    async def start(self) -> None:
        """
        Start the Kafka stream processing engine and begin consuming messages.
        """
        logger.info("Starting Kafka stream processing engine")
        try:
            # Make sure all topics exist
            topics_admin = TopicAdmin(self._config)
            topics_admin.create_topics([self._config.request_topic,
                                        self._config.response_topic])

            # Start the stream processing engine
            backend: Kafka = self._config.get_kafka_backend()
            self._stream_engine = create_engine(
                backend=backend,
                title=self._config.title,
                serializer=EventSerializer()
            )

            # Create and add a stream for incoming requests
            stream = Stream(
                topics=[self._config.request_topic],
                name=self._config.title,
                func=self._on_record,
                middlewares=[middleware.Middleware(EventDeserializer)],
                config={
                    "group_id": self._config.group_id,
                    "client_id": self._config.client_id,
                    "auto_offset_reset": "earliest",
                    "enable_auto_commit": True
                },
                backend=backend
            )
            self._stream_engine.add_stream(stream)
            # self._agent_registry.start(self._stream_engine)

            await self._stream_engine.start()

        except Exception as e:
            logger.error(f"Failed to start Kafka stream engine: {e}")
            raise

        self._started = True
        logger.info("Kafka stream processing engine started")

    async def stop(self) -> None:
        """
        Stop the Kafka stream processing engine and wait for background tasks to finish.
        """
        # Wait for all background tasks to complete
        final_tasks_results = await asyncio.gather(*self._background_tasks, return_exceptions=True)
        for task_result in final_tasks_results:
            if isinstance(task_result, Exception):
                logger.error("Error in background task", exc_info=task_result)

        if self._stream_engine is not None and self._started:
            await self._stream_engine.stop()
            # await self._agent_registry.stop()

    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None
    ) -> Any:
        """
        Send a message to a specific agent via Kafka and await a response.

        Args:
            message: The message payload.
            recipient: The agent to receive the message.
            sender: The agent sending the message.
            cancellation_token: Optional cancellation token.
            message_id: Optional message ID.

        Returns:
            The response from the recipient agent.
        """
        if not self._started:
            raise RuntimeError("KafkaWorkerAgentRuntime is not started. Call start() before publishing messages.")
        if message_id is None:
            message_id = str(uuid.uuid4())

        message_type = self._serialization_registry.type_name(message)
        with self._trace_helper.trace_block(
            "create", recipient, parent=None, extraAttributes={"message_type": message_type}
        ):
            # Create a future to await the response
            future = asyncio.get_event_loop().create_future()
            request_id = await self._get_new_request_id()
            self._pending_requests[request_id] = future

            sender_id = sender or AgentId("unknown", "unknown")
            topic_id = TopicId(type="unknown", source="unknown")

            # Serialize the message
            serialized_message = self._serialization_registry.serialize(
                message, type_name=message_type, data_content_type=JSON_DATA_CONTENT_TYPE
            )
            telemetry_metadata = get_telemetry_grpc_metadata()

            # Build the message object
            msg = Message(
                message_type=MessageType.SEND,
                request_id=request_id,
                message_id=message_id,
                payload_format=message_type,
                agent_id=sender_id,
                topic_id=topic_id,
                recipient=recipient,
                payload=serialized_message,
                metadata=telemetry_metadata
            )

            # Send the message in the background
            self._add_background_task(
                self._send_message(
                    message = msg,
                    telemetry_metadata=telemetry_metadata,
                    recipient=recipient)
            )
            return await future

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None,
    ) -> None:
        """
        Publish a message to a Kafka topic (broadcast).

        Args:
            message: The message payload.
            topic_id: The topic to publish to.
            sender: The agent sending the message.
            cancellation_token: Optional cancellation token.
            message_id: Optional message ID.
        """
        if not self._started:
            raise RuntimeError("KafkaWorkerAgentRuntime is not started. Call start() before publishing messages.")
        if message_id is None:
            message_id = str(uuid.uuid4())

        message_type = self._serialization_registry.type_name(message)
        with self._trace_helper.trace_block(
            "create", topic_id, parent=None, extraAttributes={"message_type": message_type}
        ):
            # Serialize the message
            serialized_message = self._serialization_registry.serialize(
                message, type_name=message_type, data_content_type=JSON_DATA_CONTENT_TYPE
            )
            telemetry_metadata = get_telemetry_grpc_metadata()

            attributes = {
                "id": message_id,
                "source": topic_id.source,
                "type": topic_id.type,
                "attributes": {
                    _constants.AGENT_SENDER_TYPE_ATTR: sender.type if sender else None,
                    _constants.AGENT_SENDER_KEY_ATTR: sender.key if sender else None,
                    _constants.DATA_CONTENT_TYPE_ATTR: JSON_DATA_CONTENT_TYPE,
                    _constants.DATA_SCHEMA_ATTR: message_type,
                    _constants.MESSAGE_KIND_ATTR: _constants.MESSAGE_KIND_VALUE_PUBLISH,
                },
                _constants.DATA_CONTENT_TYPE_ATTR: JSON_DATA_CONTENT_TYPE,
                _constants.DATA_SCHEMA_ATTR: message_type,
                _constants.MESSAGE_KIND_ATTR: _constants.MESSAGE_KIND_VALUE_PUBLISH,
                _constants.AGENT_SENDER_TYPE_ATTR: sender.type if sender else None,
                _constants.AGENT_SENDER_KEY_ATTR: sender.key if sender else None,
            }

            cloud_evt: CloudEvent = CloudEvent(
                attributes=attributes,
                data=serialized_message,
            )

            # Send the message in the background
            self._add_background_task(
                self._send_message(
                    message=cloud_evt,
                    recipient=topic_id,
                    telemetry_metadata=telemetry_metadata)
            )

    async def remove_subscription(self, id: str) -> None:
        """
        Remove a subscription by its ID.
        """
        await self._subscription_manager.remove_subscription(id)

    async def add_subscription(self, subscription: Subscription) -> None:
        """
        Add a new subscription.
        """
        await self._subscription_manager.add_subscription(subscription)

    async def register_factory(
        self,
        type: str | AgentType,
        agent_factory: Callable[[], T | Awaitable[T]],
        *,
        expected_class: type[T] | None = None
    ) -> AgentType:
        """
        Register a factory for creating agents of a given type.

        Args:
            type: The agent type.
            agent_factory: The factory function.
            expected_class: Optionally enforce the agent class.

        Returns:
            The registered AgentType.
        """
        if isinstance(type, str):
            type = AgentType(type)

        if type.type in self._agent_factories:
            raise ValueError(f"Agent with type {type} already exists.")
        # if self._agent_registry.is_registered(type):
        #     raise ValueError(f"Agent with id {type} already registered.")

        async def factory_wrapper() -> T:
            maybe_agent_instance = agent_factory()
            if inspect.isawaitable(maybe_agent_instance):
                agent_instance = await maybe_agent_instance
            else:
                agent_instance = maybe_agent_instance

            if expected_class is not None and type_func_alias(agent_instance) != expected_class:
                raise ValueError("Factory registered using the wrong type.")

            return agent_instance

        self._agent_factories[type.type] = factory_wrapper
        # await self._agent_registry.register_agent(type)
        return type

    async def register_agent_instance(
        self,
        agent_instance: Agent,
        agent_id: AgentId,
    ) -> AgentId:
        """
        Register a specific agent instance with a given ID.

        Args:
            agent_instance: The agent instance.
            agent_id: The agent's ID.

        Returns:
            The registered AgentId.
        """
        def agent_factory() -> Agent:
            raise RuntimeError(
                "Agent factory was invoked for an agent instance that was not registered. This is likely due to the agent type being incorrectly subscribed to a topic. If this exception occurs when publishing a message to the DefaultTopicId, then it is likely that `skip_class_subscriptions` needs to be turned off when registering the agent."
            )

        if agent_id in self._instantiated_agents:
            raise ValueError(f"Agent with id {agent_id} already exists.")

        if agent_id.type not in self._agent_factories:
            self._agent_factories[agent_id.type] = agent_factory
            self._agent_instance_types[agent_id.type] = type_func_alias(agent_instance)
        else:
            if self._agent_factories[agent_id.type].__code__ != agent_factory.__code__:
                raise ValueError("Agent factories and agent instances cannot be registered to the same type.")
            if self._agent_instance_types[agent_id.type] != type_func_alias(agent_instance):
                raise ValueError("Agent instances must be the same object type.")

        await agent_instance.bind_id_and_runtime(id=agent_id, runtime=self)
        self._instantiated_agents[agent_id] = agent_instance

        return agent_id

    async def save_state(self) -> Mapping[str, Any]:
        """
        Save the runtime state (not implemented).
        """
        raise NotImplementedError("Saving state is not yet implemented.")

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """
        Load the runtime state (not implemented).
        """
        raise NotImplementedError("Loading state is not yet implemented.")

    async def agent_metadata(self, agent: AgentId) -> AgentMetadata:
        """
        Get agent metadata (not implemented).
        """
        raise NotImplementedError("Agent metadata is not yet implemented.")

    async def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]:
        """
        Save agent state (not implemented).
        """
        raise NotImplementedError("Agent save_state is not yet implemented.")

    async def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None:
        """
        Load agent state (not implemented).
        """
        raise NotImplementedError("Agent load_state is not yet implemented.")

    async def try_get_underlying_agent_instance(self, id: AgentId, type: Type[T] = Agent) -> T:  # type: ignore[assignment]
        if id.type not in self._agent_factories:
            raise LookupError(f"Agent with name {id.type} not found.")

        # TODO: check if remote
        agent_instance = await self._get_agent(id)

        if not isinstance(agent_instance, type):
            raise TypeError(f"Agent with name {id.type} is not of type {type.__name__}")

        return agent_instance

    async def _invoke_agent_factory(
        self,
        agent_factory: Callable[[], T | Awaitable[T]] | Callable[[AgentRuntime, AgentId], T | Awaitable[T]],
        agent_id: AgentId,
    ) -> T:
        """
        Invoke an agent factory, supporting both 0-arg and 2-arg signatures.

        Args:
            agent_factory: The factory function.
            agent_id: The agent's ID.

        Returns:
            The created agent instance.
        """
        with AgentInstantiationContext.populate_context((self, agent_id)):
            params = inspect.signature(agent_factory).parameters
            if len(params) == 0:
                factory_one = cast(Callable[[], T], agent_factory)
                agent = factory_one()
            elif len(params) == 2:
                warnings.warn(
                    "Agent factories that take two arguments are deprecated. Use AgentInstantiationContext instead. Two arg factories will be removed in a future version.",
                    stacklevel=2,
                )
                factory_two = cast(Callable[[AgentRuntime, AgentId], T], agent_factory)
                agent = factory_two(self, agent_id)
            else:
                raise ValueError("Agent factory must take 0 or 2 arguments.")

            if inspect.isawaitable(agent):
                agent = cast(T, await agent)

        return agent

    async def _send_message(
        self,
        message: Message | CloudEvent,
        telemetry_metadata: Mapping[str, str],
        recipient: AgentId | TopicId = None,
    ) -> None:
        """
        Send a message to Kafka using the configured stream engine.

        Args:
            message: The message to send.
            telemetry_metadata: Telemetry metadata for tracing.
            recipient: The recipient agent or topic.
        """
        if not self._started:
            raise RuntimeError("KafkaWorkerAgentRuntime is not started. Call start() before sending messages.")

        try:
            await self._stream_engine.send(
                topic=self._config.request_topic,
                value=message,
                key=recipient.__str__(),
                headers={},
                serializer=EventSerializer()
            )
        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            raise RuntimeError(f"Failed to send message: {e}") from e

    async def _get_new_request_id(self) -> str:
        """
        Generate a new unique request ID for correlating requests and responses.
        """
        async with self._pending_requests_lock:
            self._next_request_id += 1
            return str(self._next_request_id)

    async def _on_record(self, cr: ConsumerRecord, stream: Stream, send: Send) -> None:
        """
        Callback for processing incoming Kafka records.

        Args:
            cr: The consumed record.
            stream: The stream object.
            send: The send function for producing responses.
        """
        if isinstance(cr.value, Message):
            # Route based on a message type
            if cr.value.message_type == MessageType.RESPONSE:
                self._add_background_task(self._process_response(cr.value))
            elif cr.value.message_type == MessageType.REQUEST:
                self._add_background_task(self._process_request(cr.value, send))
            return

        if isinstance(cr.value, CloudEvent):
            # Process as a CloudEvent
            await self._process_event(cr.value)
            return

        logger.error(f"Received unknown event type: {cr.value}. Expected 'CloudEvent' or 'Message'.")

    async def _process_event(self, event: CloudEvent) -> None:
        """
        Process an incoming CloudEvent message.

        Args:
            event: The CloudEvent to process.
        """
        event_attributes = event.get_attributes()
        sender: AgentId | None = None
        if (_constants.AGENT_SENDER_TYPE_ATTR in event_attributes and
                event_attributes[_constants.AGENT_SENDER_TYPE_ATTR] is not None and
                _constants.AGENT_SENDER_KEY_ATTR in event_attributes and
                event_attributes[_constants.AGENT_SENDER_KEY_ATTR] is not None):
            sender = AgentId(event_attributes[_constants.AGENT_SENDER_TYPE_ATTR],
                             event_attributes[_constants.AGENT_SENDER_KEY_ATTR],)
        topic_id = TopicId(event.type, event.source)
        recipients = await self._subscription_manager.get_subscribed_recipients(topic_id)
        message_content_type = event_attributes[_constants.DATA_CONTENT_TYPE_ATTR]
        message_type = event_attributes[_constants.DATA_SCHEMA_ATTR]

        if message_content_type == JSON_DATA_CONTENT_TYPE:
            message = self._serialization_registry.deserialize(
                event.data, type_name=message_type, data_content_type=message_content_type
            )
        else:
            raise ValueError(f"Unsupported message content type: {message_content_type}")

        topic_type_suffix = topic_id.type.split(":", maxsplit=1)[1] if ":" in topic_id.type else ""
        is_rpc = topic_type_suffix == _constants.MESSAGE_KIND_VALUE_RPC_REQUEST
        is_marked_rpc_type = (
            _constants.MESSAGE_KIND_ATTR in event_attributes
            and event_attributes[_constants.MESSAGE_KIND_ATTR] == _constants.MESSAGE_KIND_VALUE_RPC_REQUEST
        )
        if is_rpc and not is_marked_rpc_type:
            warnings.warn("Received RPC request with topic type suffix but not marked as RPC request.", stacklevel=2)

        responses: List[Awaitable[Any]] = []
        for agent_id in recipients:
            if agent_id == sender:
                continue
            message_context = MessageContext(
                sender=sender,
                topic_id=topic_id,
                is_rpc=is_rpc,
                cancellation_token=CancellationToken(),
                message_id=event.id,
            )
            agent = await self._get_agent(agent_id)
            with MessageHandlerContext.populate_context(agent.id):

                def stringify_attributes(attributes: Mapping[str, Any]) -> Mapping[str, str]:
                    result: Dict[str, str | None] = {}
                    for key, value in attributes.items():
                        if isinstance(value, str):
                            result[key] = value
                        elif value is None:
                            result[key] = None
                        else:
                            result[key] = str(value)

                    return result

                async def send_message(agent: Agent, msg_ctx: MessageContext) -> Any:
                    with self._trace_helper.trace_block("process",
                                                        agent.id,
                                                        parent=stringify_attributes(event.attributes),
                                                        extraAttributes={"message_type": message_type}):
                        await agent.on_message(message, ctx=msg_ctx)

                future = send_message(agent, message_context)
            responses.append(future)
        # Wait for all responses.
        try:
            result = await asyncio.gather(*responses, return_exceptions=True)
            for res in result:
                if isinstance(res, Exception):
                    logger.error("Error processing event", exc_info=res)
        except BaseException as e:
            logger.error("Error handling event", exc_info=e)

    async def _process_request(self, response: Message, send: Send) -> None:
        """
        Process an incoming request message, invoke the agent, and send a response.

        Args:
            response: The incoming request message.
            send: The send function for producing responses.
        """
        recipient = response.recipient
        sender = response.agent_id
        if sender is None:
            logger.info(f"Processing request from unknown source to {recipient}")
        else:
            logger.info(f"Processing request from {sender} to {recipient}")

        # Deserialize the message payload
        message = self._serialization_registry.deserialize(
            response.payload,
            type_name=response.payload_type,
            data_content_type=response.payload_format,
        )

        # Get the recipient agent
        rec_agent = await self._get_agent(recipient)
        message_context = MessageContext(
            sender=sender,
            topic_id=None,
            is_rpc=True,
            cancellation_token=CancellationToken(),
            message_id=response.request_id,
        )

        try:
            with MessageHandlerContext.populate_context(rec_agent.id):
                with self._trace_helper.trace_block(
                    "process",
                    rec_agent.id,
                    parent=response.metadata,
                    attributes={"request_id": response.request_id},
                    extraAttributes={"message_type": response.payload_type},
                ):
                    result = await rec_agent.on_message(message, ctx=message_context)
        except BaseException as e:
            # Send error response if agent processing fails
            response_message = Message(
                request_id=response.request_id,
                error=str(e),
                metadata=get_telemetry_grpc_metadata()
            )
            await send(
                topic=self._config.response_topic,
                value=response_message.to_dict(),
                key=recipient,
                serializer=EventSerializer()
            )
            return

        # Serialize and send the successful response
        result_type = self._serialization_registry.type_name(result)
        serialized_result = self._serialization_registry.serialize(
            result, type_name=result_type, data_content_type=JSON_DATA_CONTENT_TYPE
        )

        response_message = Message(
            message_type=MessageType.RESPONSE,
            request_id=response.request_id,
            payload=serialized_result,
            payload_type=result_type,
            payload_format=JSON_DATA_CONTENT_TYPE,
            agent_id=rec_agent.id,
            recipient=sender,
            metadata=get_telemetry_grpc_metadata(),
        )
        await send(
            topic=self._config.response_topic,
            value=response_message.to_dict(),
            key=recipient,
            serializer=EventSerializer()
        )

    async def _process_response(self, response: Message) -> None:
        """
        Process an incoming response message and complete the corresponding future.

        Args:
            response: The response message.
        """
        with self._trace_helper.trace_block(
            "ack",
            None,
            parent=response.metadata,
            attributes={"request_id": response.request_id},
            extraAttributes={"message_type": response.payload_format},
        ):
            result = self._serialization_registry.deserialize(
                response.payload,
                type_name=response.payload_type,
                data_content_type=response.payload_format,
            )
            future = self._pending_requests.pop(response.request_id)
            if response.error and len(response.error) > 0:
                future.set_exception(Exception(response.error))
            else:
                future.set_result(result)

    async def _get_agent(self, agent_id: AgentId) -> Agent:
        """
        Retrieve or instantiate an agent by its ID.

        Args:
            agent_id: The agent's ID.

        Returns:
            The agent instance.
        """
        if agent_id in self._instantiated_agents:
            return self._instantiated_agents[agent_id]

        if agent_id.type not in self._agent_factories:
            raise ValueError(f"Agent with name {agent_id.type} not found.")

        agent_factory = self._agent_factories[agent_id.type]
        agent = await self._invoke_agent_factory(agent_factory, agent_id)
        self._instantiated_agents[agent_id] = agent
        return agent

    def _add_background_task(self, coro: Awaitable[Any]) -> None:
        """
        Add a coroutine as a background task and track its completion.

        Args:
            coro: The coroutine to run in the background.
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(_raise_on_exception)
        task.add_done_callback(self._background_tasks.discard)

    def add_message_serializer(self, serializer: MessageSerializer[Any] | Sequence[MessageSerializer[Any]]) -> None:
        self._serialization_registry.add_serializer(serializer)
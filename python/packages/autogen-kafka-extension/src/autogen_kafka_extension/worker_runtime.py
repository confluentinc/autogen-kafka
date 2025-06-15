import asyncio
import logging
import uuid
from asyncio import Future
from typing import Dict, Callable, Awaitable, TypeVar, Any, Sequence, Mapping, Type

from autogen_core import (
    AgentRuntime, Agent, AgentId, Subscription, TopicId, CancellationToken,
    JSON_DATA_CONTENT_TYPE, AgentType, AgentMetadata, MessageSerializer,
)
from autogen_core._runtime_impl_helpers import SubscriptionManager
from autogen_core._serialization import SerializationRegistry
from autogen_core._telemetry import TraceHelper, MessageRuntimeTracingConfig, get_telemetry_grpc_metadata
from cloudevents.pydantic import CloudEvent
from kstreams import ConsumerRecord, Stream, Send
from opentelemetry.trace import TracerProvider

from autogen_kafka_extension import constants
from autogen_kafka_extension.agent_registry import AgentRegistry
from autogen_kafka_extension.agent_manager import AgentManager
from autogen_kafka_extension.background_task_manager import BackgroundTaskManager
from autogen_kafka_extension.events.message import Message, MessageType
from autogen_kafka_extension.message_processor import MessageProcessor
from autogen_kafka_extension.streaming_service import StreamingService
from autogen_kafka_extension.subscription_service import SubscriptionService
from autogen_kafka_extension.worker_config import WorkerConfig
from autogen_kafka_extension.events.message_serdes import EventSerializer

T = TypeVar("T", bound=Agent)
logger = logging.getLogger(__name__)


class KafkaWorkerAgentRuntime(AgentRuntime):
    """
    A Kafka worker agent runtime that processes messages from Kafka topics.
    Extends AgentRuntime to provide Kafka-specific functionality for consuming
    and processing messages from configured Kafka topics.
    """

    @property
    def is_started(self) -> bool:
        """Check if the Kafka worker runtime has been started."""
        return self._started

    @property
    def subscription_service(self) -> SubscriptionService:
        return self._subscription_svc

    def __init__(
        self,
        config: WorkerConfig,
        tracer_provider: TracerProvider | None = None
    ) -> None:
        """Initialize a new KafkaWorkerAgentRuntime instance."""
        super().__init__()
        
        # Initialize tracing
        self._trace_helper = TraceHelper(tracer_provider, MessageRuntimeTracingConfig("Worker Runtime"))

        # Runtime state
        self._started: bool = False
        self._config = config

        # Core services
        self._serialization_registry = SerializationRegistry()

        # Kafka components
        self._streaming_svc: StreamingService = StreamingService(config)
        self._agent_registry : AgentRegistry = AgentRegistry(config=config,
                                                             streaming=self._streaming_svc)
        self._subscription_svc: SubscriptionService = SubscriptionService(config=self._config,
                                                                          streaming=self._streaming_svc)

        # Component managers
        self._agent_manager = AgentManager(self)
        self._background_task_manager = BackgroundTaskManager()
        self._message_processor = MessageProcessor(
            self._agent_manager,
            self._serialization_registry,
            self._subscription_svc,
            self._trace_helper,
            self._config
        )

        # Request/response handling
        self._pending_requests: Dict[str, Future[Any]] = {}
        self._pending_requests_lock = asyncio.Lock()
        self._next_request_id = 0

    async def start(self) -> None:
        """Start the Kafka stream processing engine and begin consuming messages."""
        logger.info("Starting Kafka stream processing engine")
        try:
            self._streaming_svc.create_and_add_stream(
                name=self._config.title,
                topics=[self._config.request_topic],
                group_id=self._config.group_id,
                client_id=self._config.client_id,
                func=self._on_record
            )

            await self._streaming_svc.start()
        except Exception as e:
            logger.error(f"Failed to start Kafka stream engine: {e}")
            raise

        self._started = True
        logger.info("Kafka stream processing engine started")

    async def stop(self) -> None:
        """Stop the Kafka stream processing engine and wait for background tasks to finish."""
        if not self._started:
            return

        await self._background_task_manager.wait_for_completion()

        logger.info("Stopping Kafka stream processing engine")
        await self._subscription_svc.unsubscribe_all()

        if self._streaming_svc is not None and self._started:
            try:
                await self._streaming_svc.stop()
            except Exception as e:
                logger.error(f"Failed to stop Kafka stream engine: {e}")

    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None
    ) -> Any:
        """Send a message to a specific agent via Kafka and await a response."""
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
                message_type=MessageType.REQUEST,
                request_id=request_id,
                message_id=message_id,
                payload_format=JSON_DATA_CONTENT_TYPE,
                payload_type=message_type,
                agent_id=sender_id,
                topic_id=topic_id,
                recipient=recipient,
                payload=serialized_message,
                metadata=telemetry_metadata
            )

            # Send the message in the background
            self._background_task_manager.add_task(
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
        """Publish a message to a Kafka topic (broadcast)."""
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
                    constants.AGENT_SENDER_TYPE_ATTR: sender.type if sender else None,
                    constants.AGENT_SENDER_KEY_ATTR: sender.key if sender else None,
                    constants.DATA_CONTENT_TYPE_ATTR: JSON_DATA_CONTENT_TYPE,
                    constants.DATA_SCHEMA_ATTR: message_type,
                    constants.MESSAGE_KIND_ATTR: constants.MESSAGE_KIND_VALUE_PUBLISH,
                },
                constants.DATA_CONTENT_TYPE_ATTR: JSON_DATA_CONTENT_TYPE,
                constants.DATA_SCHEMA_ATTR: message_type,
                constants.MESSAGE_KIND_ATTR: constants.MESSAGE_KIND_VALUE_PUBLISH,
                constants.AGENT_SENDER_TYPE_ATTR: sender.type if sender else None,
                constants.AGENT_SENDER_KEY_ATTR: sender.key if sender else None,
            }

            cloud_evt: CloudEvent = CloudEvent(
                attributes=attributes,
                data=serialized_message,
            )

            # Send the message in the background
            self._background_task_manager.add_task(
                self._send_message(
                    message=cloud_evt,
                    recipient=topic_id,
                    telemetry_metadata=telemetry_metadata)
            )

    async def remove_subscription(self, id: str) -> None:
        """Remove a subscription by its ID."""
        await self._subscription_svc.remove_subscription(id)

    async def add_subscription(self, subscription: Subscription) -> None:
        """Add a new subscription."""
        await self._subscription_svc.add_subscription(subscription)

    async def register_factory(
        self,
        type: str | AgentType,
        agent_factory: Callable[[], T | Awaitable[T]],
        *,
        expected_class: type[T] | None = None
    ) -> AgentType:
        """Register a factory for creating agents of a given type."""
        return await self._agent_manager.register_factory(
            type, agent_factory, self._agent_registry, expected_class=expected_class
        )

    async def register_agent_instance(
        self,
        agent_instance: Agent,
        agent_id: AgentId,
    ) -> AgentId:
        """Register a specific agent instance with a given ID."""
        return await self._agent_manager.register_instance(agent_instance, agent_id)

    async def save_state(self) -> Mapping[str, Any]:
        """Save the runtime state (not implemented)."""
        raise NotImplementedError("Saving state is not yet implemented.")

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load the runtime state (not implemented)."""
        raise NotImplementedError("Loading state is not yet implemented.")

    async def agent_metadata(self, agent: AgentId) -> AgentMetadata:
        """Get agent metadata (not implemented)."""
        raise NotImplementedError("Agent metadata is not yet implemented.")

    async def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]:
        """Save agent state (not implemented)."""
        raise NotImplementedError("Agent save_state is not yet implemented.")

    async def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None:
        """Load agent state (not implemented)."""
        raise NotImplementedError("Agent load_state is not yet implemented.")

    async def try_get_underlying_agent_instance(self, id: AgentId, type: Type[T] = Agent) -> T:  # type: ignore[assignment]
        return await self._agent_manager.try_get_underlying_agent_instance(id, type)

    async def _send_message(
        self,
        message: Message | CloudEvent,
        telemetry_metadata: Mapping[str, str],
        recipient: AgentId | TopicId = None,
    ) -> None:
        """Send a message to Kafka using the configured stream engine."""
        if not self._started:
            raise RuntimeError("KafkaWorkerAgentRuntime is not started. Call start() before sending messages.")

        try:
            await self._streaming_svc.send(
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
        """Generate a new unique request ID for correlating requests and responses."""
        async with self._pending_requests_lock:
            self._next_request_id += 1
            return str(self._next_request_id)

    async def _on_record(self, cr: ConsumerRecord, stream: Stream, send: Send) -> None:
        """Callback for processing incoming Kafka records."""
        if isinstance(cr.value, Message):
            # Route based on a message type
            if cr.value.message_type == MessageType.RESPONSE:
                self._background_task_manager.add_task(
                    self._process_response(cr.value)
                )
            elif cr.value.message_type == MessageType.REQUEST:
                self._background_task_manager.add_task(
                    self._message_processor.process_request(cr.value, send)
                )
            return

        if isinstance(cr.value, CloudEvent):
            # Process as a CloudEvent
            await self._message_processor.process_event(cr.value)
            return

        logger.error(f"Received unknown event type: {cr.value}. Expected 'CloudEvent' or 'Message'.")

    async def _process_response(self, response: Message) -> None:
        """Process an incoming response message and complete the corresponding future."""
        self._message_processor.process_response(response, self._pending_requests)

    def add_message_serializer(self, serializer: MessageSerializer[Any] | Sequence[MessageSerializer[Any]]) -> None:
        self._serialization_registry.add_serializer(serializer)
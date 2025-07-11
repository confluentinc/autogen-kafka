import asyncio
import logging
import warnings
from typing import Dict, Any, Awaitable, List, Mapping

from autogen_core import (
    Agent, AgentId, TopicId, CancellationToken, JSON_DATA_CONTENT_TYPE,
    MessageContext, MessageHandlerContext
)
from autogen_core._serialization import SerializationRegistry
from autogen_core._telemetry import TraceHelper, get_telemetry_grpc_metadata
from azure.core.messaging import CloudEvent
from kstreams import Send

from autogen_kafka_extension import KafkaAgentRuntimeConfig
from autogen_kafka_extension.runtimes.services import constants
from autogen_kafka_extension.runtimes.services.agent_manager import AgentManager
from autogen_kafka_extension.runtimes.services.subscription_service import SubscriptionService
from autogen_kafka_extension.shared.events.events_serdes import EventSerializer
from autogen_kafka_extension.shared.events.request_event import RequestEvent
from autogen_kafka_extension.shared.events.response_event import ResponseEvent

logger = logging.getLogger(__name__)

class MessageProcessor:
    """Handles processing of different message types."""
    
    def __init__(
        self,
        agent_manager: AgentManager,
        serialization_registry: SerializationRegistry,
        subscription_service: SubscriptionService,
        trace_helper: TraceHelper,
        config: KafkaAgentRuntimeConfig,
    ):
        """Initialize the MessageProcessor with required dependencies.
        
        Args:
            agent_manager: Manages agent instances and lifecycle
            serialization_registry: Handles message serialization and deserialization
            subscription_service: Manages topic subscriptions and recipient lookups
            trace_helper: Provides distributed tracing capabilities
            config: Worker configuration settings including topic names
        """
        self._agent_manager = agent_manager
        self._serialization_registry = serialization_registry
        self._subscription_service = subscription_service
        self._trace_helper = trace_helper
        self._config = config

        self._response_serializer = EventSerializer(
            topic=config.response_topic,
            source_type=ResponseEvent,
            kafka_utils=self._config.kafka_config.utils()
        )
    
    async def process_event(self, event: CloudEvent) -> None:
        """Process an incoming CloudEvent message.
        
        Deserializes the event payload, determines recipients based on subscriptions,
        and delivers the message to all subscribed agents. Handles both regular
        messages and RPC requests.
        
        Args:
            event: The CloudEvent containing the message payload and metadata
            
        Raises:
            ValueError: If the message content type is unsupported
        """
        event_attributes = event.extensions
        sender: AgentId | None = None
        if (constants.AGENT_SENDER_TYPE_ATTR in event_attributes and
                event_attributes[constants.AGENT_SENDER_TYPE_ATTR] is not None and
                constants.AGENT_SENDER_KEY_ATTR in event_attributes and
                event_attributes[constants.AGENT_SENDER_KEY_ATTR] is not None):
            sender = AgentId(event_attributes[constants.AGENT_SENDER_TYPE_ATTR],
                             event_attributes[constants.AGENT_SENDER_KEY_ATTR], )
        topic_id = TopicId(event.type, event.source)
        recipients = await self._subscription_service.get_subscribed_recipients(topic_id)
        message_content_type = event.datacontenttype
        message_type = event.dataschema

        if message_content_type == JSON_DATA_CONTENT_TYPE:
            message = self._serialization_registry.deserialize(
                event.data, type_name=message_type, data_content_type=message_content_type
            )
        else:
            raise ValueError(f"Unsupported message content type: {message_content_type}")

        topic_type_suffix = topic_id.type.split(":", maxsplit=1)[1] if ":" in topic_id.type else ""
        is_rpc = topic_type_suffix == constants.MESSAGE_KIND_VALUE_RPC_REQUEST
        is_marked_rpc_type = (
                constants.MESSAGE_KIND_ATTR in event_attributes
                and event_attributes[constants.MESSAGE_KIND_ATTR] == constants.MESSAGE_KIND_VALUE_RPC_REQUEST
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
            agent = await self._agent_manager.get_agent(agent_id)
            with MessageHandlerContext.populate_context(agent.id):

                def stringify_attributes(attributes: Mapping[str, Any]) -> Mapping[str, str | None]:
                    attr: Dict[str, str | None] = {}
                    for key, value in attributes.items():
                        if isinstance(value, str):
                            attr[key] = value
                        elif value is None:
                            attr[key] = None
                        else:
                            attr[key] = str(value)
                    return attr

                async def send_message(agent: Agent, msg_ctx: MessageContext) -> Any:
                    with self._trace_helper.trace_block("process",
                                                        agent.id,
                                                        parent=stringify_attributes(event.extensions),
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

    async def process_request(self, request: RequestEvent, send: Send) -> None:
        """Process an incoming request message, invoke the agent, and send a response.

        This method handles direct agent-to-agent RPC requests by:
        1. Deserializing the request payload using the serialization registry
        2. Retrieving the target agent instance from the agent manager
        3. Creating a message context with RPC metadata
        4. Invoking the agent's message handler with distributed tracing
        5. Serializing and sending the response back to the requester
        6. Handling errors by sending error responses with telemetry data

        The method ensures that even if agent processing fails, a response is always
        sent back to prevent the requester from waiting indefinitely.

        Args:
            request: The request event containing:
                    - recipient: Target agent ID
                    - agent_id: Sender agent ID (optional)
                    - payload: Serialized message data
                    - payload_type: Message type for deserialization
                    - payload_format: Content type (e.g., JSON)
                    - request_id: Unique identifier for request correlation
                    - metadata: Tracing and telemetry metadata
            send: Kafka producer function for sending response messages back to
                 the response topic. Must be async callable.

        Returns:
            None: This method doesn't return a value but sends responses via Kafka

        Raises:
            Exception: Any exception during message processing is caught and converted
                      to an error response. The original exception is logged but not
                      re-raised to prevent disrupting the message processing loop.

        Example:
            ```python
            request = RequestEvent(
                recipient=AgentId("chat_agent", "instance_1"),
                payload=b'{"text": "Hello"}',
                payload_type="ChatMessage",
                request_id="req_123"
            )
            await processor.process_request(request, kafka_send_func)
            ```
        """
        try:
            return await self._process_request(request, send)
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            # Send an error response if agent processing fails
            response_message = ResponseEvent(
                request_id=request.request_id,
                error=str(e),
                metadata=get_telemetry_grpc_metadata()
            )
            try:
                await send(
                    topic=self._config.response_topic,
                    value=response_message,
                    key=request.request_id,
                    serializer=self._response_serializer
                )
            except Exception as e:
                logger.error(f"Failed to send response message: {e}")

    async def _process_request(self, request: RequestEvent, send: Send) -> None:

        recipient = request.recipient

        # Get the recipient agent
        rec_agent = await self._agent_manager.get_agent(recipient)
        if rec_agent is None:
            # The agent is not registered or not found, Ignore the request (Was not for this instance)
            return

        sender = request.agent_id
        if sender is None:
            logger.info(f"Processing request from unknown source to {recipient}")
        else:
            logger.info(f"Processing request from {sender} to {recipient}")

        # Deserialize the message payload
        message = self._serialization_registry.deserialize(
            request.payload,
            type_name=request.payload_type,
            data_content_type=request.payload_format,
        )

        message_context = MessageContext(
            sender=sender,
            topic_id=None,
            is_rpc=True,
            cancellation_token=CancellationToken(),
            message_id=request.request_id,
        )

        with MessageHandlerContext.populate_context(rec_agent.id):
            with self._trace_helper.trace_block(
                "process",
                rec_agent.id,
                parent=request.metadata,
                attributes={"request_id": request.request_id},
                extraAttributes={"message_type": request.payload_type},
            ):
                result = await rec_agent.on_message(message, ctx=message_context)

        result_type = self._serialization_registry.type_name(result)
        serialized_result = self._serialization_registry.serialize(
            result, type_name=result_type, data_content_type=JSON_DATA_CONTENT_TYPE
        )

        response_message = ResponseEvent(
            request_id=request.request_id,
            payload=serialized_result,
            payload_type=result_type,
            serialization_format=JSON_DATA_CONTENT_TYPE,
            sender=rec_agent.id,
            recipient=sender,
            metadata=get_telemetry_grpc_metadata(),
        )
        await send(
            topic=self._config.response_topic,
            value=response_message,
            key=request.request_id,
            serializer=self._response_serializer,
            headers={}
        )

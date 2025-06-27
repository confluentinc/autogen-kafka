import asyncio
import logging
import uuid
from asyncio import Future
from typing import Optional, Any, Sequence, Dict

from autogen_core import AgentId, TopicId, JSON_DATA_CONTENT_TYPE
from autogen_core._serialization import SerializationRegistry, MessageSerializer
from autogen_core._telemetry import get_telemetry_grpc_metadata, TraceHelper
from azure.core.messaging import CloudEvent
from kstreams import ConsumerRecord, Send, Stream
from opentelemetry.trace import TracerProvider

from autogen_kafka_extension import KafkaAgentRuntimeConfig
from autogen_kafka_extension.runtimes.services import constants
from autogen_kafka_extension.shared.events.events_serdes import EventSerializer
from autogen_kafka_extension.shared.events.request_event import RequestEvent
from autogen_kafka_extension.shared.events.response_event import ResponseEvent
from autogen_kafka_extension.shared.streaming_worker_base import StreamingWorkerBase
from autogen_kafka_extension.shared.streaming_service import StreamingService

logger = logging.getLogger(__name__)

class MessagingClient(StreamingWorkerBase[KafkaAgentRuntimeConfig]):
    """A Kafka-based messaging client for asynchronous agent communication.
    
    The MessagingClient provides a high-level interface for sending and receiving messages
    between agents using Apache Kafka as the underlying messaging infrastructure. It supports
    both point-to-point messaging with response correlation and broadcast messaging to topics.
    
    Key Features:
    - **Point-to-Point Messaging**: Send messages to specific agents and await responses
    - **Broadcast Messaging**: Publish messages to topics for multiple subscribers
    - **Request/Response Correlation**: Automatically correlates responses with pending requests
    - **Message Serialization**: Handles automatic serialization/deserialization of messages
    - **Telemetry Integration**: Provides distributed tracing and monitoring capabilities
    - **Background Processing**: Non-blocking message sending with background task management
    
    The class extends StreamingWorkerBase and integrates with the Kafka streaming ecosystem
    to provide reliable, scalable message delivery between distributed agents.
    
    Usage Example:
        ```python
        config = WorkerConfig(request_topic="requests", response_topic="responses")
        client = MessagingClient(config)
        
        await client.start()
        
        # Send a message to a specific agent
        response = await client.send_message(
            message=MyMessage("hello"),
            recipient=AgentId("agent", "123")
        )
        
        # Broadcast a message to a topic
        await client.publish_message(
            message=MyMessage("broadcast"),
            topic_id=TopicId("notifications", "system")
        )
        
        await client.stop()
        ```
    
    Thread Safety:
        The MessagingClient is designed to be used from a single asyncio event loop.
        Internal operations use asyncio locks to ensure thread-safe access to shared state.
    """

    def __init__(self,
                 config: KafkaAgentRuntimeConfig,
                 streaming_service: Optional[StreamingService] = None,
                 monitoring: Optional[TraceHelper] | Optional[TracerProvider] = None,
                 serialization_registry: SerializationRegistry = SerializationRegistry(),
                 ) -> None:
        """Initialize the MessagingClient for sending and receiving messages via Kafka.
        
        Args:
            config: Worker configuration containing Kafka topics and connection settings
            streaming_service: Optional streaming service for Kafka operations. If None, a default will be created
            monitoring: Optional telemetry monitoring for tracing. Can be either TraceHelper or TracerProvider
            serialization_registry: Registry for message serialization/deserialization. Defaults to a new instance
        """
        super().__init__(config=config,
                         topic=config.response_topic,
                         monitoring=monitoring,
                         streaming_service=streaming_service,
                         serialization_registry=serialization_registry,
                         target_type=ResponseEvent)
        # Request/response handling
        self._pending_requests: Dict[str, Future[Any]] = {}
        self._pending_requests_lock = asyncio.Lock()
        self._next_request_id = 0
        self._cloud_event_serializer = EventSerializer(
            topic = config.publish_topic,
            source_type = CloudEvent,
            schema_registry_service = self._kafka_config.get_schema_registry_service())
        self._request_serializer = EventSerializer(
            topic = config.request_topic,
            source_type = RequestEvent,
            schema_registry_service = self._kafka_config.get_schema_registry_service()
        )

    def add_message_serializer(self, serializer: MessageSerializer[Any] | Sequence[MessageSerializer[Any]]) -> None:
        """Add one or more message serializers to the serialization registry.
        
        Args:
            serializer: A single MessageSerializer or a sequence of MessageSerializers to add
        """
        self._serialization_registry.add_serializer(serializer)

    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        message_id: str | None = None
    ) -> Any:
        """Send a message to a specific agent via Kafka and await a response.
        
        Args:
            message: The message object to send
            recipient: The AgentId of the intended recipient
            sender: Optional AgentId of the sender. If None, defaults to "unknown"
            message_id: Optional unique message identifier. If None, a UUID will be generated
            
        Returns:
            The response message from the recipient agent
            
        Raises:
            RuntimeError: If the messaging client is not started
        """
        if not self.is_started:
            raise RuntimeError(f"{self.name} is not started. Call start() before publishing messages.")

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
            msg = RequestEvent(
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
                super().send_message(
                    message = msg,
                    topic = self._config.request_topic,
                    recipient=recipient,
                    serializer=self._request_serializer)
            )
            return await future

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        sender: AgentId | None = None,
        message_id: str | None = None,
    ) -> None:
        """Publish a message to a Kafka topic (broadcast to all subscribers).
        
        Args:
            message: The message object to publish
            topic_id: The TopicId specifying the target topic
            sender: Optional AgentId of the sender. If None, sender info will be omitted
            message_id: Optional unique message identifier. If None, a UUID will be generated
            
        Raises:
            RuntimeError: If the messaging client is not started
        """
        if not self.is_started:
            raise RuntimeError(f"{self.name} is not started. Call start() before publishing messages.")
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

            cloud_evt: CloudEvent = CloudEvent[bytes](
                source=topic_id.source,
                type=topic_id.type,
                id=message_id,
                data=serialized_message,
                dataschema=message_type,
                datacontenttype=JSON_DATA_CONTENT_TYPE,
                subject=topic_id.source,
                extensions={
                    constants.AGENT_SENDER_TYPE_ATTR: sender.type if sender else None,
                    constants.AGENT_SENDER_KEY_ATTR: sender.key if sender else None,
                    constants.DATA_CONTENT_TYPE_ATTR: JSON_DATA_CONTENT_TYPE,
                    constants.DATA_SCHEMA_ATTR: message_type,
                    constants.MESSAGE_KIND_ATTR: constants.MESSAGE_KIND_VALUE_PUBLISH,
                },
            )

            # Send the message in the background
            self._background_task_manager.add_task(
                super().send_message(
                    message=cloud_evt,
                    topic=self._config.publish_topic,
                    recipient=topic_id,
                    serializer=self._cloud_event_serializer)
                )

    async def _get_new_request_id(self) -> str:
        """Generate a new unique request ID for correlating requests and responses.
        
        Returns:
            A unique string identifier for the request
        """
        async with self._pending_requests_lock:
            self._next_request_id += 1
            return str(self._next_request_id)

    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
        """Handle incoming response events from Kafka and resolve pending request futures.
        
        Args:
            record: The Kafka consumer record containing the response event
            stream: The Kafka stream instance
            send: The send function for publishing messages
        """
        if not isinstance(record.value, ResponseEvent):
            logger.error(f"Received non-ResponseEvent record: {record}. Expected 'ResponseEvent'.")
            return

        response = record.value

        with self._trace_helper.trace_block(
            "ack",
            None,
            parent=response.metadata,
            attributes={"request_id": response.request_id},
            extraAttributes={"message_type": response.payload_type},
        ):
            result = self._serialization_registry.deserialize(
                response.payload,
                type_name=response.payload_type,
                data_content_type=response.serialization_format,
            )
            future = self._pending_requests.pop(response.request_id)
            if response.error and len(response.error) > 0:
                future.set_exception(Exception(response.error))
            else:
                future.set_result(result)
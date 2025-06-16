import asyncio
import logging
import uuid
from asyncio import Future
from typing import Optional, Any, Sequence, Dict

from autogen_core import AgentId, CancellationToken, TopicId, JSON_DATA_CONTENT_TYPE
from autogen_core._serialization import SerializationRegistry, MessageSerializer
from autogen_core._telemetry import get_telemetry_grpc_metadata, TraceHelper
from cloudevents.pydantic import CloudEvent
from kstreams import ConsumerRecord, Send, Stream
from opentelemetry.trace import TracerProvider

from autogen_kafka_extension import constants
from autogen_kafka_extension.events.request_event import RequestEvent
from autogen_kafka_extension.events.response_event import ResponseEvent
from autogen_kafka_extension.streaming_worker_base import StreamingWorkerBase
from autogen_kafka_extension.streaming_service import StreamingService
from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)

class MessagingClient(StreamingWorkerBase):

    def __init__(self,
                 config: WorkerConfig,
                 streaming_service: Optional[StreamingService] = None,
                 trace_helper: TraceHelper | None = None,
                 tracer_provider: TracerProvider | None = None,
                 serialization_registry: SerializationRegistry = SerializationRegistry()
                 ) -> None:
        super().__init__(config=config,
                         name="MessagingClient",
                         topic=config.response_topic,
                         trace_helper=trace_helper,
                         tracer_provider=tracer_provider,
                         streaming_service=streaming_service,
                         serialization_registry=serialization_registry)
        # Request/response handling
        self._pending_requests: Dict[str, Future[Any]] = {}
        self._pending_requests_lock = asyncio.Lock()
        self._next_request_id = 0

    def add_message_serializer(self, serializer: MessageSerializer[Any] | Sequence[MessageSerializer[Any]]) -> None:
        self._serialization_registry.add_serializer(serializer)

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
        if not self._is_started:
            raise RuntimeError(f"{self._name} is not started. Call start() before publishing messages.")

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
                self._send_message(
                    message = msg,
                    topic = self._config.request_topic,
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
        if not self.is_started():
            raise RuntimeError(f"{self._name} is not started. Call start() before publishing messages.")
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
                    topic=self._config.request_topic,
                    recipient=topic_id)
            )

    async def _get_new_request_id(self) -> str:
        """Generate a new unique request ID for correlating requests and responses."""
        async with self._pending_requests_lock:
            self._next_request_id += 1
            return str(self._next_request_id)

    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
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
import logging
from typing import Optional

from autogen_core import AgentId, TopicId
from autogen_core._serialization import SerializationRegistry
from autogen_core._telemetry import TraceHelper, MessageRuntimeTracingConfig
from cloudevents.abstract import CloudEvent
from kstreams import ConsumerRecord, Stream, Send
from opentelemetry.trace import TracerProvider

from autogen_kafka_extension.background_task_manager import BackgroundTaskManager
from autogen_kafka_extension.events.registration_event import RegistrationEvent
from autogen_kafka_extension.events.request_event import RequestEvent
from autogen_kafka_extension.events.message_serdes import EventSerializer
from autogen_kafka_extension.events.response_event import ResponseEvent
from autogen_kafka_extension.streaming_service import StreamingService
from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)

class StreamingWorkerBase:

    def __init__(self,
                 config: WorkerConfig,
                 topic: str,
                 name: str = None,
                 serialization_registry: SerializationRegistry = SerializationRegistry(),
                 trace_helper: TraceHelper | None = None,
                 tracer_provider: TracerProvider | None = None,
                 streaming_service: Optional[StreamingService] = None) -> None:
        self._background_task_manager = BackgroundTaskManager()
        self._streaming_service = streaming_service or StreamingService(config)
        self._owns_streaming_service = streaming_service is None
        # We assumed that if no streaming service is provided, we own it and can start/stop it.
        self._is_started = False
        self._name = name if name is not None else type(self).__name__
        self._topic = topic
        self._config = config
        self._serialization_registry = serialization_registry
        self._trace_helper = trace_helper if trace_helper is not None else TraceHelper(tracer_provider, MessageRuntimeTracingConfig("Worker Runtime"))

        self._setup_event_stream()

    def is_started(self) -> bool:
        """Check if the service is currently started."""
        return self._is_started

    async def start(self) -> None:
        """Start the subscription service."""
        if not self._owns_streaming_service:
            self._is_started = True
            return

        if self._is_started:
            logger.warning(f"{self._name} is already started")
            return

        await self._streaming_service.start()
        self._is_started = True
        logger.info(f"{self._name} started")

    async def stop(self) -> None:
        """Stop the subscription service."""
        if not self._owns_streaming_service:
            self._is_started = False
            return

        if not self._is_started:
            logger.warning(f"{self._name} is already stopped")
            return

        await self._background_task_manager.wait_for_completion()

        await self._streaming_service.stop()
        self._is_started = False
        logger.info(f"{self._name} stopped")

    async def _send_message(
        self,
        message: RequestEvent | CloudEvent | ResponseEvent | RegistrationEvent,
        topic: str,
        recipient: AgentId | TopicId | str = None,
    ) -> None:
        """Send a message to Kafka using the configured stream engine."""
        if not self._is_started:
            raise RuntimeError(f"{self._name} is not started. Call start() before sending messages.")

        try:
            await self._streaming_service.send(
                topic=topic,
                value=message,
                key=recipient if isinstance(recipient, str) else recipient.__str__(),
                headers={},
                serializer=EventSerializer()
            )
        except Exception as e:
            logger.error(f"Failed to send message to Kafka: {e}")
            raise RuntimeError(f"Failed to send message: {e}") from e

    def _setup_event_stream(self) -> None:
        """Configure the Kafka stream for subscription events."""
        stream_name = f"{self._config.title}_{self._name}"
        group_id = f"{self._config.group_id}_{self._name}"
        client_id = f"{self._config.client_id}_{self._name}"

        self._streaming_service.create_and_add_stream(
            name=stream_name,
            topics=[self._topic],
            group_id=group_id,
            client_id=client_id,
            func=self._handle_event
        )

    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
        raise NotImplementedError() 
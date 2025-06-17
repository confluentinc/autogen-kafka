import logging
from typing import Optional, Union
from dataclasses import dataclass

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

MessageType = Union[RequestEvent, CloudEvent, ResponseEvent, RegistrationEvent]
RecipientType = Union[AgentId, TopicId, str, None]


@dataclass
class StreamConfiguration:
    """Configuration for Kafka stream setup."""
    stream_name: str
    topics: list[str]
    group_id: str
    client_id: str


class StreamingServiceManager:
    """Manages streaming service lifecycle and ownership."""
    
    def __init__(self, streaming_service: Optional[StreamingService], config: WorkerConfig):
        self._service = streaming_service
        self._config = config
        self._owns_service = streaming_service is None
        self._is_started = False
        
        if self._service is None:
            self._service = StreamingService(config)
    
    @property
    def service(self) -> StreamingService:
        return self._service

    @property
    def is_started(self) -> bool:
        return self._is_started
    
    async def start(self) -> None:
        """Start the streaming service if owned."""
        if not self._owns_service:
            self._is_started = True
            return
            
        if self._is_started:
            return
            
        await self._service.start()
        self._is_started = True
    
    async def stop(self) -> None:
        """Stop the streaming service if owned."""
        if not self._owns_service:
            self._is_started = False
            return
            
        if not self._is_started:
            return
            
        await self._service.stop()
        self._is_started = False


class StreamingWorkerBase:
    """Base class for streaming workers with improved separation of concerns."""

    def __init__(
        self,
        config: WorkerConfig,
        topic: str,
        name: Optional[str] = None,
        serialization_registry: Optional[SerializationRegistry] = None,
        trace_helper: Optional[TraceHelper] = None,
        tracer_provider: Optional[TracerProvider] = None,
        streaming_service: Optional[StreamingService] = None
    ) -> None:
        self._config = config
        self._topic = topic
        self._name = name or type(self).__name__
        
        # Initialize components
        self._background_task_manager = BackgroundTaskManager()
        self._service_manager = StreamingServiceManager(streaming_service, config)
        self._serialization_registry = serialization_registry or SerializationRegistry()
        self._trace_helper = trace_helper or TraceHelper(
            tracer_provider, 
            MessageRuntimeTracingConfig("Worker Runtime")
        )
        
        # Setup stream
        self._setup_event_stream()

    @property
    def name(self) -> str:
        """Get the worker name."""
        return self._name

    @property
    def is_started(self) -> bool:
        """Check if the worker is currently started."""
        return self._service_manager.is_started

    async def start(self) -> None:
        """Start the streaming worker."""
        if self.is_started:
            logger.warning(f"Worker '{self._name}' is already started")
            return

        try:
            await self._service_manager.start()
            logger.info(f"Worker '{self._name}' started successfully")
        except Exception as e:
            logger.error(f"Failed to start worker '{self._name}': {e}")
            raise RuntimeError(f"Failed to start worker: {e}") from e

    async def stop(self) -> None:
        """Stop the streaming worker."""
        if not self.is_started:
            logger.warning(f"Worker '{self._name}' is already stopped")
            return

        try:
            # Wait for background tasks to complete
            await self._background_task_manager.wait_for_completion()
            
            await self._service_manager.stop()
            logger.info(f"Worker '{self._name}' stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop worker '{self._name}': {e}")
            raise RuntimeError(f"Failed to stop worker: {e}") from e

    async def send_message(
        self,
        message: MessageType,
        topic: str,
        recipient: RecipientType = None,
    ) -> None:
        """Send a message to Kafka with improved error handling and type safety."""
        self._ensure_started()
        
        try:
            key = self._get_message_key(recipient)
            await self._service_manager.service.send(
                topic=topic,
                value=message,
                key=key,
                headers={},
                serializer=EventSerializer()
            )
            logger.debug(f"Message sent successfully to topic '{topic}' with key '{key}'")
        except Exception as e:
            logger.error(f"Failed to send message to topic '{topic}': {e}")
            raise RuntimeError(f"Failed to send message to topic '{topic}': {e}") from e

    def _ensure_started(self) -> None:
        """Ensure the worker is started before performing operations."""
        if not self.is_started:
            raise RuntimeError(
                f"Worker '{self._name}' is not started. Call start() before sending messages."
            )

    def _get_message_key(self, recipient: RecipientType) -> Optional[str]:
        """Get the message key from recipient."""
        if recipient is None:
            return None
        if isinstance(recipient, str):
            return recipient
        return str(recipient)

    def _create_stream_configuration(self) -> StreamConfiguration:
        """Create stream configuration with proper naming."""
        return StreamConfiguration(
            stream_name=f"{self._config.title}_{self._name}",
            topics=[self._topic],
            group_id=f"{self._config.group_id}_{self._name}",
            client_id=f"{self._config.client_id}_{self._name}"
        )

    def _setup_event_stream(self) -> None:
        """Configure the Kafka stream for subscription events."""
        stream_config = self._create_stream_configuration()
        
        self._service_manager.service.create_and_add_stream(
            name=stream_config.stream_name,
            topics=stream_config.topics,
            group_id=stream_config.group_id,
            client_id=stream_config.client_id,
            func=self._handle_event
        )
        
        logger.debug(f"Stream configured for worker '{self._name}' on topics {stream_config.topics}")

    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
        """Handle incoming events. Must be implemented by subclasses."""
        raise NotImplementedError(
            f"Subclasses must implement _handle_event method. "
            f"Worker '{self._name}' received event but no handler is defined."
        ) 
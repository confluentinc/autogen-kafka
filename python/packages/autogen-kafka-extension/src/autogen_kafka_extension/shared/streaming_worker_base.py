import logging
from abc import abstractmethod, ABC
from typing import Optional, Union, TypeVar, Generic, Any

from autogen_core import AgentId, TopicId
from autogen_core._serialization import SerializationRegistry
from autogen_core._telemetry import TraceHelper, MessageRuntimeTracingConfig
from opentelemetry.trace import TracerProvider

from .consumer_record import ConsumerRecord
from .message_producer import MessageProducer
from .schema_utils import SchemaUtils
from .stream import Stream, EventHandler
from ..config.service_base_config import ServiceBaseConfig
from .background_task_manager import BackgroundTaskManager
from .events.events_serdes import EventSerializer
from .streaming_service import StreamingService
from ..config.kafka_config import KafkaConfig
from ..config.streaming_config import StreamingServiceConfig

logger = logging.getLogger(__name__)

RecipientType = Union[AgentId, TopicId, str, None]

class StreamingServiceManager:
    """Manages the lifecycle and ownership of a StreamingService instance.

    This class abstracts the creation, startup, and shutdown of a StreamingService.
    It supports both externally provided StreamingService instances and internally
    managed ones, and only manages the lifecycle of services it creates.
    """
    _service: StreamingService
    
    def __init__(self,
                 streaming_service: StreamingService | None,
                 config: KafkaConfig):
        """Initialize the StreamingServiceManager.

        Args:
            streaming_service: An existing StreamingService instance, or None to create one.
            config: KafkaConfig used to create a StreamingService if not provided.
        """
        self._config = config
        self._owns_service = streaming_service is None
        self._is_started = False
        
        if streaming_service is None:
            self._service = StreamingService(config)
        else:
            self._service = streaming_service
    
    @property
    def service(self) -> StreamingService:
        """Return the managed StreamingService instance."""
        return self._service

    @property
    def is_started(self) -> bool:
        """Return True if the streaming service is started."""
        return self._is_started
    
    async def start(self) -> None:
        """Start the streaming service if owned by this manager."""
        if not self._owns_service:
            self._is_started = True
            return
            
        if self._is_started:
            return
            
        await self._service.start()
        self._is_started = True
    
    async def stop(self) -> None:
        """Stop the streaming service if owned by this manager."""
        if not self._owns_service:
            self._is_started = False
            return
            
        if not self._is_started:
            return
            
        await self._service.stop()
        self._is_started = False

T = TypeVar('T', bound=ServiceBaseConfig)

class StreamingWorkerBase(EventHandler, ABC, Generic[T]):
    """Abstract base class for streaming workers.

    Provides common logic for managing streaming service lifecycle, background tasks,
    serialization, and telemetry. Subclasses must implement the _handle_event method.
    """

    def __init__(
        self,
        config: T,
        topic: str,
        target_type: type,
        *,
        name: str | None = None,
        serialization_registry: SerializationRegistry | None = None,
        monitoring: TraceHelper | TracerProvider | None = None,
        streaming_service: StreamingService | None = None,
        schema_str: str | None = None,
    ) -> None:
        """Initialize the streaming worker.

        Args:
            config: Worker configuration.
            topic: Kafka topic to subscribe to.
            target_type: Type of messages to process.
            name: Optional human-readable worker name.
            serialization_registry: Optional SerializationRegistry.
            monitoring: Optional TraceHelper or TracerProvider for telemetry.
            streaming_service: Optional externally provided StreamingService.
            schema_str: Optional schema string for the topic.
            stream_cls: Optional custom Stream class.
        """
        self._config = config
        self._kafka_config : KafkaConfig = config.kafka_config
        self._topic = topic
        self._name = name or type(self).__name__

        # Initialize components
        self._background_task_manager = BackgroundTaskManager()
        self._service_manager = StreamingServiceManager(streaming_service, self._kafka_config)
        self._serialization_registry = serialization_registry or SerializationRegistry()

        schema = schema_str if schema_str else SchemaUtils.get_schema_str(target_type)
        # Make sure the schema is registered or upgraded
        self._config.kafka_config.utils().register_or_upgrade_schema(topic = topic,
                                                               for_key=False,
                                                               schema_str=schema,
                                                               schema_type="JSON")

        if monitoring is None:
            self._trace_helper = TraceHelper(tracer_provider=None,
                                             instrumentation_builder_config = MessageRuntimeTracingConfig("Worker Runtime"))
        elif isinstance(monitoring, TracerProvider):
            self._trace_helper = TraceHelper(monitoring, MessageRuntimeTracingConfig("Worker Runtime"))
        else:
            self._trace_helper = monitoring

        # Setup stream
        self._setup_event_stream(target_type=target_type,
                                 schema_str=schema_str)

    @property
    def name(self) -> str:
        """Return the worker's name."""
        return self._name

    @property
    def is_started(self) -> bool:
        """Return True if the worker is started."""
        return self._service_manager.is_started

    async def start(self) -> None:
        """Start the worker and its streaming service."""
        logger.info(f"Starting worker '{self._name}'")

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
        """Stop the worker and its streaming service."""
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

    async def wait_for_streams_to_start(self, timeout: float = 30.0, check_interval: float = 0.1) -> bool:
        """Wait until all stream consumers are running.

        Args:
            timeout: Maximum time to wait in seconds.
            check_interval: Time between status checks in seconds.

        Returns:
            True if all streams are running within the timeout, False otherwise.

        Raises:
            ValueError: If timeout or check_interval are invalid.
            RuntimeError: If the worker is not started.
        """
        if timeout <= 0:
            raise ValueError("Timeout must be a positive number")
        if not self.is_started:
            raise RuntimeError(f"Worker '{self._name}' is not started. Call start() before waiting for streams.")

        logger.debug(f"Waiting for all streams to start for worker '{self._name}' with timeout {timeout} seconds")

        await self._ensure_started()
        return await self._service_manager.service.wait_for_streams_to_start(timeout, check_interval)

    def get_stream_names(self) -> set[str]:
        """Return the set of stream names managed by this worker.

        Raises:
            RuntimeError: If the worker is not started.
        """
        if not self.is_started:
            raise RuntimeError(f"Worker '{self._name}' is not started")
        return self._service_manager.service.get_stream_names()

    def is_stream_running(self, stream_name: str) -> bool:
        """Return True if the specified stream is running.

        Args:
            stream_name: Name of the stream.

        Raises:
            KeyError: If the stream does not exist.
            RuntimeError: If the worker is not started.
        """
        if not self.is_started:
            raise RuntimeError(f"Worker '{self._name}' is not started")
        return self._service_manager.service.is_stream_running(stream_name)

    def are_all_streams_running(self) -> bool:
        """Return True if all streams are running.

        Raises:
            RuntimeError: If the worker is not started.
        """
        if not self.is_started:
            raise RuntimeError(f"Worker '{self._name}' is not started")
        return self._service_manager.service.are_all_streams_running()

    def get_stream_status(self) -> dict[str, bool]:
        """Return a dict mapping stream names to their running status.

        Raises:
            RuntimeError: If the worker is not started.
        """
        if not self.is_started:
            raise RuntimeError(f"Worker '{self._name}' is not started")
        return self._service_manager.service.get_stream_status()

    async def send_message(
        self,
        message: Any | None,
        topic: str,
        serializer: EventSerializer,
        *,
        recipient: RecipientType = None,
    ) -> None:
        """Send a message to Kafka.

        Args:
            message: The message to send.
            topic: Kafka topic.
            serializer: Serializer for the message.
            recipient: Optional recipient for key partitioning.

        Raises:
            RuntimeError: If the worker is not started or sending fails.
        """
        await self._ensure_started()
        
        try:
            key = self._get_message_key(recipient)
            await self._service_manager.service.send(
                topic=topic,
                value=message,
                key=key,
                headers={},
                serializer=serializer
            )
            logger.debug(f"Message sent successfully to topic '{topic}' with key '{key}'")
        except Exception as e:
            logger.error(f"Failed to send message to topic '{topic}': {e}")
            raise RuntimeError(f"Failed to send message to topic '{topic}': {e}") from e

    async def _ensure_started(self) -> None:
        """Raise RuntimeError if the worker is not started."""
        if not self.is_started:
            raise RuntimeError(
                f"Worker '{self._name}' is not started. Call start() before sending messages."
            )

    def _get_message_key(self, recipient: RecipientType) -> Optional[str]:
        """Convert recipient to a string key for Kafka partitioning."""
        if recipient is None:
            return None
        if isinstance(recipient, str):
            return recipient
        return str(recipient)

    def _setup_event_stream(self,
                            target_type: type,
                            *,
                            schema_str: Optional[str] = None) -> None:
        """Configure the Kafka stream for this worker.

        Sets up the stream and registers the event handler.
        """
        stream_config = StreamingServiceConfig(
            name=f"{self._kafka_config.name}_{self._name}",
            topic=self._topic,
            group_id=f"{self._kafka_config.group_id}_{self._name}",
            client_id=f"{self._kafka_config.client_id}_{self._name}",
            auto_offset_reset=self._kafka_config.auto_offset_reset,
            target_type=target_type,
        )

        self._service_manager.service.create_and_add_stream(
            stream_config=stream_config,
            func=self,
            schema_str=schema_str
        )
        
        logger.debug(f"Stream configured for worker '{self._name}' on topic {stream_config.topic}")

    @abstractmethod
    async def handle_event(self, record: ConsumerRecord, stream: Stream, producer: MessageProducer) -> None:
        """Abstract event handler to be implemented by subclasses.

        Args:
            record: The Kafka consumer record.
            stream: The Stream instance.
            producer: Function to send messages.

        Raises:
            NotImplementedError: Always, unless implemented by subclass.
        """
        raise NotImplementedError(
            f"Subclasses must implement _handle_event method. "
            f"Worker '{self._name}' received event but no handler is defined."
        )

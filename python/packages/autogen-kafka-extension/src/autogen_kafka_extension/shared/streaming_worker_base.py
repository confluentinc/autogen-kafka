import logging
from abc import abstractmethod, ABC
from typing import Optional, Union, TypeVar, Generic, Any

from autogen_core import AgentId, TopicId
from autogen_core._serialization import SerializationRegistry
from autogen_core._telemetry import TraceHelper, MessageRuntimeTracingConfig
from kstreams import ConsumerRecord, Stream, Send
from kstreams.serializers import Serializer
from opentelemetry.trace import TracerProvider

from ..config.service_base_config import ServiceBaseConfig
from .background_task_manager import BackgroundTaskManager
from .events.events_serdes import EventSerializer
from .streaming_service import StreamingService
from ..config.kafka_config import KafkaConfig
from ..config.streaming_config import StreamingServiceConfig

logger = logging.getLogger(__name__)

RecipientType = Union[AgentId, TopicId, str, None]

class StreamingServiceManager:
    """Manages streaming service lifecycle and ownership.
    
    This class provides a wrapper around StreamingService to handle its lifecycle
    management, including creation, startup, and shutdown. It supports both
    externally provided streaming services and internally managed ones.
    
    The manager implements an ownership pattern where it only controls the lifecycle
    of streaming services it creates internally. Externally provided services are
    not started or stopped by this manager.
    
    Attributes:
        _service (StreamingService): The managed streaming service instance.
        _config (WorkerConfig): Configuration for the worker.
        _owns_service (bool): Whether this manager owns the service lifecycle.
        _is_started (bool): Current state of the streaming service.
    """
    
    _service: StreamingService
    
    def __init__(self,
                 streaming_service: Optional[StreamingService],
                 config: KafkaConfig):
        """Initialize the streaming service manager.
        
        Args:
            streaming_service (Optional[StreamingService]): An existing streaming service
                to manage. If None, a new service will be created internally.
            config (WorkerConfig): Configuration object containing worker settings.
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
        """Get the managed streaming service instance.
        
        Returns:
            StreamingService: The streaming service being managed.
        """
        return self._service

    @property
    def is_started(self) -> bool:
        """Check if the streaming service is currently started.
        
        Returns:
            bool: True if the service is started, False otherwise.
        """
        return self._is_started
    
    async def start(self) -> None:
        """Start the streaming service if owned by this manager.
        
        Only starts the service if this manager owns it (i.e., it was created
        internally). For externally provided services, this method only updates
        the internal state tracking.
        
        Raises:
            Exception: If the service fails to start.
        """
        if not self._owns_service:
            self._is_started = True
            return
            
        if self._is_started:
            return
            
        await self._service.start()
        self._is_started = True
    
    async def stop(self) -> None:
        """Stop the streaming service if owned by this manager.
        
        Only stops the service if this manager owns it. For externally provided
        services, this method only updates the internal state tracking.
        
        Raises:
            Exception: If the service fails to stop.
        """
        if not self._owns_service:
            self._is_started = False
            return
            
        if not self._is_started:
            return
            
        await self._service.stop()
        self._is_started = False

T = TypeVar('T', bound=ServiceBaseConfig)

class StreamingWorkerBase(ABC, Generic[T]):
    """Base class for streaming workers with improved separation of concerns.
    
    This abstract base class provides the foundation for building streaming workers
    that process messages from Kafka topics. It handles the common functionality
    such as service lifecycle management, message serialization, background task
    coordination, and telemetry integration.
    
    The class follows a composition pattern, delegating specific responsibilities
    to specialized components like StreamingServiceManager for service lifecycle
    and BackgroundTaskManager for task coordination.
    
    Subclasses must implement the `_handle_event` method to define specific
    message processing logic.
    
    Attributes:
        _config (WorkerConfig): Worker configuration settings.
        _topic (str): Primary Kafka topic this worker subscribes to.
        _name (str): Human-readable name for this worker instance.
        _background_task_manager (BackgroundTaskManager): Manages background tasks.
        _service_manager (StreamingServiceManager): Manages streaming service lifecycle.
        _serialization_registry (SerializationRegistry): Handles message serialization.
        _trace_helper (TraceHelper): Provides telemetry and tracing capabilities.
    """

    def __init__(
        self,
        config: T,
        topic: str,
        target_type: type,
        *,
        name: Optional[str] = None,
        serialization_registry: Optional[SerializationRegistry] = None,
        monitoring: Optional[TraceHelper] | Optional[TracerProvider] = None,
        streaming_service: Optional[StreamingService] = None
    ) -> None:
        """Initialize the streaming worker base.
        
        Args:
            config (ServiceBaseConfig): Configuration object containing worker settings.
            topic (str): The primary Kafka topic this worker will subscribe to for
                incoming messages.
            target_type (type): The type of messages this worker will process.
            name (Optional[str]): Human-readable name for this worker instance.
                If None, defaults to the class name.
            serialization_registry (Optional[SerializationRegistry]): Registry for
                handling message serialization/deserialization. If None, a default
                registry is created.
            monitoring (Optional[TraceHelper] | Optional[TracerProvider]): Telemetry
                configuration for tracing and monitoring. Can be either a TraceHelper
                instance or a TracerProvider. If None, creates a default TraceHelper.
            streaming_service (Optional[StreamingService]): An existing streaming
                service to use. If None, a new service will be created internally.
        """
        self._config = config
        self._kafka_config : KafkaConfig = config.kafka_config
        self._topic = topic
        self._name = name or type(self).__name__
        
        # Initialize components
        self._background_task_manager = BackgroundTaskManager()
        self._service_manager = StreamingServiceManager(streaming_service, self._kafka_config)
        self._serialization_registry = serialization_registry or SerializationRegistry()

        if monitoring is None:
            self._trace_helper = TraceHelper(tracer_provider=None,
                                             instrumentation_builder_config = MessageRuntimeTracingConfig("Worker Runtime"))
        elif isinstance(monitoring, TracerProvider):
            self._trace_helper = TraceHelper(monitoring, MessageRuntimeTracingConfig("Worker Runtime"))
        else:
            self._trace_helper = monitoring

        # Setup stream
        self._setup_event_stream(target_type=target_type)

    @property
    def name(self) -> str:
        """Get the worker name.
        
        Returns:
            str: The human-readable name of this worker instance.
        """
        return self._name

    @property
    def is_started(self) -> bool:
        """Check if the worker is currently started.
        
        Returns:
            bool: True if the worker is running and ready to process messages,
                False otherwise.
        """
        return self._service_manager.is_started

    async def start(self) -> None:
        """Start the streaming worker.
        
        Initializes and starts all necessary components for message processing.
        This includes starting the underlying streaming service and setting up
        the message processing pipeline.

        Raises:
            RuntimeError: If the worker fails to start or is already started.
        """
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
        """Stop the streaming worker.
        
        Gracefully shuts down the worker by waiting for background tasks to
        complete and then stopping the streaming service. This ensures no
        messages are lost during shutdown.
        
        Raises:
            RuntimeError: If the worker fails to stop or is already stopped.
        """
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
        """Wait until all stream consumers managed by this worker are running.
        
        This method delegates to the underlying streaming service to wait for all
        registered stream consumers to start and be actively polling for messages.
        A stream is considered running when its underlying Kafka consumer has started
        and is ready to process messages, regardless of whether it has processed any
        messages yet.
        
        Args:
            timeout (float): Maximum time to wait in seconds. Defaults to 30.0 seconds.
            check_interval (float): Time between status checks in seconds. Defaults to 0.1 seconds.
            
        Returns:
            bool: True if all stream consumers are running within the timeout, False if timeout occurred.
            
        Raises:
            ValueError: If timeout or check_interval are invalid values.
            RuntimeError: If the worker is not started.
            
        Example:
            ```python
            # Start the worker
            await worker.start()
            
            # Wait for all stream consumers to start
            if await worker.wait_for_streams_to_start():
                print("All stream consumers are running!")
            else:
                print("Timeout: Not all stream consumers started")
            ```
        """
        await self._ensure_started()
        return await self._service_manager.service.wait_for_streams_to_start(timeout, check_interval)

    def get_stream_names(self) -> set[str]:
        """Get the names of all streams managed by this worker.
        
        Returns:
            set[str]: Set of stream names that have been registered with this worker.
            
        Raises:
            RuntimeError: If the worker is not started.
        """
        if not self.is_started:
            raise RuntimeError(f"Worker '{self._name}' is not started")
        return self._service_manager.service.get_stream_names()

    def is_stream_running(self, stream_name: str) -> bool:
        """Check if a specific stream consumer managed by this worker is currently running.
        
        A stream is considered running when its underlying Kafka consumer has started
        and is actively polling for messages, regardless of whether it has processed
        any messages yet.
        
        Args:
            stream_name (str): The name of the stream to check.
            
        Returns:
            bool: True if the stream consumer is running, False otherwise.
            
        Raises:
            KeyError: If no stream with the given name exists.
            RuntimeError: If the worker is not started.
        """
        if not self.is_started:
            raise RuntimeError(f"Worker '{self._name}' is not started")
        return self._service_manager.service.is_stream_running(stream_name)

    def are_all_streams_running(self) -> bool:
        """Check if all stream consumers managed by this worker are currently running.
        
        A stream is considered running when its underlying Kafka consumer has started
        and is actively polling for messages, regardless of whether it has processed
        any messages yet.
        
        Returns:
            bool: True if all stream consumers are running, False if any consumer is not 
                  running or if no streams are registered.
                  
        Raises:
            RuntimeError: If the worker is not started.
        """
        if not self.is_started:
            raise RuntimeError(f"Worker '{self._name}' is not started")
        return self._service_manager.service.are_all_streams_running()

    def get_stream_status(self) -> dict[str, bool]:
        """Get the running status of all stream consumers managed by this worker.
        
        Returns the current status of each stream consumer, where True indicates the
        consumer is running and actively polling for messages.
        
        Returns:
            dict[str, bool]: Dictionary mapping stream names to their consumer running status.
            
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
        """Send a message to Kafka with improved error handling and type safety.
        
        Serializes and sends a message to the specified Kafka topic. The message
        key is derived from the recipient parameter to enable proper partitioning
        and routing.
        
        Args:
            message (Any | None): The message to send.
            topic (str): The Kafka topic to send the message to.
            recipient (RecipientType, optional): The intended recipient of the
                message. Can be AgentId, TopicId, string, or None. This is used
                to generate the message key for partitioning.
            serializer (Serializer): Custom serializer for the message.
        
        Raises:
            RuntimeError: If the worker is not started or message sending fails.
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
        """Ensure the worker is started before performing operations.
        
        Internal helper method that validates the worker state before allowing
        message operations.
        
        Raises:
            RuntimeError: If the worker is not currently started.
        """
        if not self.is_started:
            raise RuntimeError(
                f"Worker '{self._name}' is not started. Call start() before sending messages."
            )

    def _get_message_key(self, recipient: RecipientType) -> Optional[str]:
        """Get the message key from recipient for Kafka partitioning.
        
        Converts various recipient types into a string key suitable for Kafka
        message partitioning. This ensures messages for the same recipient
        are processed in order.
        
        Args:
            recipient (RecipientType): The message recipient, which can be
                AgentId, TopicId, string, or None.
        
        Returns:
            Optional[str]: The message key as a string, or None if no recipient
                is specified.
        """
        if recipient is None:
            return None
        if isinstance(recipient, str):
            return recipient
        return str(recipient)

    def _setup_event_stream(self, target_type: type,) -> None:
        """Configure the Kafka stream for subscription events.
        
        Internal method that sets up the Kafka stream using the streaming service.
        This includes configuring topics, consumer groups, and message handlers.
        The stream is configured to call `_handle_event` for each incoming message.
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
            func=self._handle_event,
        )
        
        logger.debug(f"Stream configured for worker '{self._name}' on topic {stream_config.topic}")

    @abstractmethod
    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
        """Handle incoming events. Must be implemented by subclasses.
        
        Abstract method that subclasses must implement to define their specific
        message processing logic. This method is called for each message received
        from the subscribed Kafka topics.
        
        Args:
            record (ConsumerRecord): The Kafka consumer record containing the
                message data, headers, and metadata.
            stream (Stream): The Kafka stream instance for accessing stream operations.
            send (Send): Function for sending messages to other topics.
        
        Raises:
            NotImplementedError: Always raised since this is an abstract method.
        """
        raise NotImplementedError(
            f"Subclasses must implement _handle_event method. "
            f"Worker '{self._name}' received event but no handler is defined."
        ) 
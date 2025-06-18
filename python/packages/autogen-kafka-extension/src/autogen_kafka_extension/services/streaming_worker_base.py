import logging
from typing import Optional, Union
from dataclasses import dataclass

from autogen_core import AgentId, TopicId
from autogen_core._serialization import SerializationRegistry
from autogen_core._telemetry import TraceHelper, MessageRuntimeTracingConfig
from cloudevents.abstract import CloudEvent
from kstreams import ConsumerRecord, Stream, Send
from opentelemetry.trace import TracerProvider

from autogen_kafka_extension.services.background_task_manager import BackgroundTaskManager
from autogen_kafka_extension.events.registration_event import RegistrationEvent
from autogen_kafka_extension.events.request_event import RequestEvent
from autogen_kafka_extension.events.message_serdes import EventSerializer
from autogen_kafka_extension.events.response_event import ResponseEvent
from autogen_kafka_extension.services.streaming_service import StreamingService
from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)

MessageType = Union[RequestEvent, CloudEvent, ResponseEvent, RegistrationEvent]
RecipientType = Union[AgentId, TopicId, str, None]


@dataclass
class StreamConfiguration:
    """Configuration for Kafka stream setup.
    
    This dataclass encapsulates all the necessary configuration parameters
    required to set up a Kafka stream for message processing.
    
    Attributes:
        stream_name (str): Unique identifier for the stream.
        topics (list[str]): List of Kafka topics to subscribe to.
        group_id (str): Consumer group ID for Kafka consumer group management.
        client_id (str): Unique client identifier for the Kafka consumer.
    """
    stream_name: str
    topics: list[str]
    group_id: str
    client_id: str


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
    
    def __init__(self, streaming_service: Optional[StreamingService], config: WorkerConfig):
        """Initialize the streaming service manager.
        
        Args:
            streaming_service (Optional[StreamingService]): An existing streaming service
                to manage. If None, a new service will be created internally.
            config (WorkerConfig): Configuration object containing worker settings.
        """
        self._service = streaming_service
        self._config = config
        self._owns_service = streaming_service is None
        self._is_started = False
        
        if self._service is None:
            self._service = StreamingService(config)
    
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


class StreamingWorkerBase:
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
        config: WorkerConfig,
        topic: str,
        name: Optional[str] = None,
        serialization_registry: Optional[SerializationRegistry] = None,
        monitoring: Optional[TraceHelper] | Optional[TracerProvider] = None,
        streaming_service: Optional[StreamingService] = None
    ) -> None:
        """Initialize the streaming worker base.
        
        Args:
            config (WorkerConfig): Configuration object containing worker settings
                such as Kafka broker information, authentication, and other runtime options.
            topic (str): The primary Kafka topic this worker will subscribe to for
                incoming messages.
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
        self._topic = topic
        self._name = name or type(self).__name__
        
        # Initialize components
        self._background_task_manager = BackgroundTaskManager()
        self._service_manager = StreamingServiceManager(streaming_service, config)
        self._serialization_registry = serialization_registry or SerializationRegistry()

        if monitoring is None:
            self._trace_helper = TraceHelper(tracer_provider=None,
                                             instrumentation_builder_config = MessageRuntimeTracingConfig("Worker Runtime"))
        elif isinstance(monitoring, TracerProvider):
            self._trace_helper = TraceHelper(monitoring, MessageRuntimeTracingConfig("Worker Runtime"))
        else:
            self._trace_helper = monitoring

        # Setup stream
        self._setup_event_stream()

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

    async def send_message(
        self,
        message: MessageType,
        topic: str,
        recipient: RecipientType = None,
    ) -> None:
        """Send a message to Kafka with improved error handling and type safety.
        
        Serializes and sends a message to the specified Kafka topic. The message
        key is derived from the recipient parameter to enable proper partitioning
        and routing.
        
        Args:
            message (MessageType): The message to send. Can be RequestEvent,
                CloudEvent, ResponseEvent, or RegistrationEvent.
            topic (str): The Kafka topic to send the message to.
            recipient (RecipientType, optional): The intended recipient of the
                message. Can be AgentId, TopicId, string, or None. This is used
                to generate the message key for partitioning.
        
        Raises:
            RuntimeError: If the worker is not started or message sending fails.
        """
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

    def _create_stream_configuration(self) -> StreamConfiguration:
        """Create stream configuration with proper naming.
        
        Generates a StreamConfiguration object with appropriate naming conventions
        that include the worker configuration and instance name to ensure uniqueness.
        
        Returns:
            StreamConfiguration: Configuration object for setting up the Kafka stream.
        """
        return StreamConfiguration(
            stream_name=f"{self._config.title}_{self._name}",
            topics=[self._topic],
            group_id=f"{self._config.group_id}_{self._name}",
            client_id=f"{self._config.client_id}_{self._name}"
        )

    def _setup_event_stream(self) -> None:
        """Configure the Kafka stream for subscription events.
        
        Internal method that sets up the Kafka stream using the streaming service.
        This includes configuring topics, consumer groups, and message handlers.
        The stream is configured to call `_handle_event` for each incoming message.
        """
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
from kstreams import Stream, middleware, StreamEngine, PrometheusMonitor, Consumer, Producer
from kstreams.types import StreamFunc
import asyncio
import threading
from typing import Dict, Set, Optional
import logging

from ..config.kafka_config import KafkaConfig
from .events.events_serdes import EventDeserializer
from ..config.streaming_config import StreamingServiceConfig

logger = logging.getLogger(__name__)


class TrackableStream(Stream):
    """
    Custom Stream class that inherits from kstreams Stream to expose running state.
    
    This class extends the base Stream functionality to provide clean access to
    the stream's running status via an is_running property.
    """

    @property
    def is_running(self) -> bool:
        """Check if this stream's consumer is currently running.
        
        A stream is considered running when its underlying Kafka consumer has started
        and is actively polling for messages, regardless of whether it has processed
        any messages yet.
        
        Returns:
            bool: True if the stream's consumer is running, False otherwise.
        """
        return self.running


class StreamingService(StreamEngine):
    """
    Kafka streaming engine that extends StreamEngine with topic management capabilities.
    
    This class provides a high-level interface for creating and managing Kafka streams
    within the autogen-kafka-extension. It combines the power of the kstreams library
    with additional features such as:
    
    - Automatic Kafka topic creation and management
    - Schema Registry integration for message serialization/deserialization  
    - Simplified stream creation and configuration
    - Individual stream running status tracking via custom TrackableStream
    - Wait for all streams to be started functionality
    
    Attributes:
        _config (KafkaConfig): Configuration for Kafka connections and settings
        _added_streams (Dict[str, TrackableStream]): Dictionary tracking all created streams by name
        _status_lock (threading.Lock): Thread-safe access to stream status tracking
    """

    def __init__(self, config: KafkaConfig):
        """
        Initialize the StreamingService with the given configuration.
        
        Sets up the underlying StreamEngine with proper serialization, monitoring,
        and creates a TopicAdminService for managing Kafka topics and stream tracking.
        
        Args:
            config (KafkaConfig): Configuration object containing Kafka broker settings,
                                Schema Registry configuration, and other connection parameters
        """
        super().__init__(
            backend=config.get_kafka_backend(),
            title=config.name,
            monitor=PrometheusMonitor(),
            consumer_class=Consumer,
            producer_class=Producer,
        )
        self._config = config

        # Stream tracking with custom TrackableStream
        self._added_streams: Dict[str, TrackableStream] = {}
        self._status_lock = threading.Lock()

    def create_and_add_stream(self,
                              stream_config: StreamingServiceConfig,
                              func: StreamFunc,
                              schema_str: Optional[str] = None) -> TrackableStream:
        """Create a Kafka stream with automatic topic management and deserialization.
        
        This method combines topic creation, stream configuration, and middleware setup
        into a single convenient operation. It handles the common pattern of creating
        a Kafka stream with event deserialization and optional topic auto-creation.
        
        The stream is configured with:
        - Automatic event deserialization using the EventDeserializer middleware
        - Schema Registry integration for type-safe message handling
        - Consumer configuration from the stream config
        - Topic auto-creation if enabled
        - Custom TrackableStream for reliable running status tracking
        
        Args:
            stream_config: Configuration object containing:
                          - topic: Kafka topic name to consume from
                          - name: Stream identifier for monitoring/debugging
                          - target_type: Expected message type for deserialization
                          - auto_create_topics: Whether to create topics automatically
                          - Consumer configuration parameters
            func: Stream processing function that handles deserialized messages.
                 Must accept (ConsumerRecord, Stream, Send) parameters and return
                 None or a ConsumerRecord.
            schema_str: Optional schema string to use for the message
                 
        Returns:
            TrackableStream: The configured and registered Kafka stream instance with
                           running status tracking capabilities. The stream is already
                           added to the StreamEngine and ready for processing.
                   
        Raises:
            KafkaException: If topic creation fails or Kafka connection issues occur
            ValueError: If stream_config is invalid or target_type is unsupported
            
        Example:
            ```python
            async def process_events(record, stream, send):
                event = record.value # Already deserialized by middleware
                print(f"Received event: {event}")
            
            config = StreamingServiceConfig(
                topic="user.events",
                name="user-processor",
                target_type=UserEvent,
                auto_create_topics=True
            )
            
            stream = service.create_and_add_stream(config, process_events)
            ```
            
        Note:
            The stream is automatically registered with the StreamEngine and will
            begin processing messages when the engine starts. Topics are created
            synchronously before stream creation if auto_create_topics is enabled.
        """

        # Create topics if requested
        if stream_config.auto_create_topics:
            self._config.utils().create_topic(stream_config.topic)

        # Create and add the stream using our custom TrackableStream
        middleware_type = middleware.Middleware(
            middleware = EventDeserializer,
            kafka_utils=self._config.utils(),
            target_type= stream_config.target_type,
            schema_str=schema_str)

        stream = TrackableStream(
            topics=stream_config.topic,
            name=stream_config.name,
            func=func,
            middlewares=[middleware_type],
            config=stream_config.get_consumer_config(),
            backend=self.backend
        )

        try:
            self.add_stream(stream)
        except Exception as e:
            logger.error(f"Failed to add stream '{stream_config.name}': {e}")
            raise e
        
        # Track the stream
        with self._status_lock:
            self._added_streams[stream_config.name] = stream

        logger.debug(f"Created stream '{stream_config.name}' for topic '{stream_config.topic}'")

        return stream

    def get_stream_names(self) -> Set[str]:
        """Get the names of all registered streams.
        
        Returns:
            Set[str]: Set of stream names that have been registered with this service.
        """
        with self._status_lock:
            return set(self._added_streams.keys())

    def is_stream_running(self, stream_name: str) -> bool:
        """Check if a specific stream's consumer is currently running.
        
        A stream is considered running when its underlying Kafka consumer
        has started and is actively polling for messages, regardless of whether
        it has processed any messages yet.
        
        Args:
            stream_name (str): The name of the stream to check.
            
        Returns:
            bool: True if the stream's consumer is running, False otherwise.
            
        Raises:
            KeyError: If no stream with the given name exists.
        """
        with self._status_lock:
            if stream_name not in self._added_streams:
                raise KeyError(f"Stream '{stream_name}' not found")
            
            stream = self._added_streams[stream_name]
            return stream.is_running

    def are_all_streams_running(self) -> bool:
        """Check if all registered streams' consumers are currently running.
        
        Returns:
            bool: True if all stream consumers are running, False if any consumer 
                  is not running or if no streams are registered.
        """
        with self._status_lock:
            if not self._added_streams:
                return False
            
            return all(stream.is_running for stream in self._added_streams.values())

    def get_stream_status(self) -> Dict[str, bool]:
        """Get the running status of all stream consumers.
        
        Returns:
            Dict[str, bool]: Dictionary mapping stream names to their consumer running status.
        """
        with self._status_lock:
            return {
                name: stream.is_running
                for name, stream in self._added_streams.items()
            }

    async def wait_for_streams_to_start(self, timeout: float = 30.0, check_interval: float = 0.1) -> bool:
        """Wait until all registered stream consumers are running.
        
        This method polls the consumer running status at regular intervals until either
        all consumers are running or the timeout is reached. It uses the custom
        TrackableStream's is_running property for reliable status checking.
        
        Args:
            timeout (float): Maximum time to wait in seconds. Defaults to 30.0 seconds.
            check_interval (float): Time between status checks in seconds. Defaults to 0.1 seconds.
            
        Returns:
            bool: True if all consumers are running within the timeout, False if timeout occurred.
            
        Raises:
            ValueError: If timeout or check_interval are negative values.
            
        Example:
            ```python
            # Wait for all streams to start before proceeding
            if await service.wait_for_streams_to_start(timeout=60.0):
                print("All streams are running!")
            else:
                print("Timeout waiting for streams to start")
            ```
        """
        if timeout < 0:
            raise ValueError("Timeout must be non-negative")
        if check_interval <= 0:
            raise ValueError("Check interval must be positive")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if self.are_all_streams_running():
                logger.info("All streams are now running")
                return True
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                stream_status = self.get_stream_status()
                running_streams = [name for name, status in stream_status.items() if status]
                not_running_streams = [name for name, status in stream_status.items() if not status]
                
                logger.warning(
                    f"Timeout waiting for streams to start after {timeout}s. "
                    f"Running: {running_streams}, Not running: {not_running_streams}"
                )
                return False
            
            await asyncio.sleep(check_interval)

    async def stop(self) -> None:
        """Stop the streaming service.
        
        This method stops the underlying StreamEngine and all associated consumers.
        """
        logger.info("Stopping streaming service")
        await super().stop()
        logger.info("Streaming service stopped")

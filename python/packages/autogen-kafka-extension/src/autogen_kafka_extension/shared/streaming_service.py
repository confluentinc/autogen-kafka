from kstreams import Stream, middleware, StreamEngine, PrometheusMonitor, Consumer, Producer
from kstreams.types import StreamFunc

from ..config.kafka_config import KafkaConfig
from .events.events_serdes import EventDeserializer
from ..config.streaming_config import StreamingServiceConfig
from .topic_admin_service import TopicAdminService


class StreamingService(StreamEngine):
    """
    Kafka streaming engine that extends StreamEngine with topic management capabilities.
    
    This class provides a high-level interface for creating and managing Kafka streams
    within the autogen-kafka-extension. It combines the power of the kstreams library
    with automatic topic management, proper serialization/deserialization, and 
    monitoring capabilities.
    
    Key Features:
    - Automatic topic creation and management
    - Built-in event serialization/deserialization
    - Prometheus monitoring integration
    - Simplified stream creation and configuration
    - Error handling and proper configuration management
    
    The service uses the WorkerConfig to configure the underlying Kafka backend and
    integrates with the TopicAdmin for topic lifecycle management.
    
    Attributes:
        _config (WorkerConfig): Configuration object containing Kafka connection details
        _topics_admin (TopicAdminService): Topic administration service for creating/managing topics
    """
    
    def __init__(self, config: KafkaConfig):
        """
        Initialize the StreamingService with the given configuration.
        
        Sets up the underlying StreamEngine with proper serialization, monitoring,
        and Kafka backend configuration. Also initializes the topic administration
        service for managing Kafka topics.
        
        Args:
            config (KafkaConfig): Configuration object containing Kafka connection
                                 details, serialization settings, and other service
                                 configuration parameters
        """
        super().__init__(
            backend=config.get_kafka_backend(),
            title=config.name,
            monitor=PrometheusMonitor(),
            consumer_class=Consumer,
            producer_class=Producer,
        )
        self._config = config
        self._topics_admin = TopicAdminService(self._config)

    def create_topics(self, topics: list[str]) -> None:
        """
        Create Kafka topics if they do not already exist.
        
        This method uses the TopicAdmin service to create the specified topics
        with the default configuration. Topics that already exist will be skipped
        without error.
        
        Args:
            topics (list[str]): List of topic names to create. Each topic name
                              should be a valid Kafka topic name following Kafka
                              naming conventions
                              
        Raises:
            KafkaException: If topic creation fails due to Kafka connectivity
                          or permission issues
        """
        self._topics_admin.create_topics(topic_names=topics)

    def create_and_add_stream(self,
                              stream_config: StreamingServiceConfig,
                              func: StreamFunc) -> Stream:
        """Create a Kafka stream with automatic topic management and deserialization.
        
        This method combines topic creation, stream configuration, and middleware setup
        into a single convenient operation. It handles the common pattern of creating
        a Kafka stream with event deserialization and optional topic auto-creation.
        
        The stream is configured with:
        - Automatic event deserialization using the EventDeserializer middleware
        - Schema Registry integration for type-safe message handling
        - Consumer configuration from the stream config
        - Topic auto-creation if enabled
        
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
                 
        Returns:
            Stream: The configured and registered Kafka stream instance. The stream
                   is already added to the StreamEngine and ready for processing.
                   
        Raises:
            KafkaException: If topic creation fails or Kafka connection issues occur
            ValueError: If stream_config is invalid or target_type is unsupported
            
        Example:
            ```python
            async def process_events(record, stream, send):
                event = record.value  # Already deserialized by middleware
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
            self.create_topics([stream_config.topic])

        # Create and add the stream
        middleware_type = middleware.Middleware(
            middleware = EventDeserializer,
            schema_registry_service=self._config.get_schema_registry_service(),
            target_type= stream_config.target_type)

        stream = Stream(
            topics=stream_config.topic,
            name=stream_config.name,
            func=func,
            middlewares=[middleware_type],
            config=stream_config.get_consumer_config(),
            backend=self.backend
        )

        self.add_stream(stream)

        return stream

from dataclasses import dataclass
from typing import Any, Optional, List

from kstreams import Stream, middleware, StreamEngine, PrometheusMonitor, Consumer, Producer
from kstreams.middleware.middleware import MiddlewareProtocol
from kstreams.types import StreamFunc

from autogen_kafka_extension.shared.events.events_serdes import EventSerializer, EventDeserializer
from autogen_kafka_extension.shared.kafka_config import KafkaConfig
from autogen_kafka_extension.shared.topic_admin_service import TopicAdminService
from autogen_kafka_extension.runtimes.worker_config import WorkerConfig


@dataclass
class StreamConfig:
    """
    Configuration for a Kafka stream.
    
    This class encapsulates all the necessary configuration parameters for creating
    and configuring a Kafka stream consumer. It provides a clean interface for
    setting up stream properties and generating the appropriate consumer configuration.
    
    Attributes:
        name (str): The name of the stream, used for identification and logging
        topics (list[str]): List of Kafka topics to consume from
        group_id (str): Base consumer group ID for the Kafka consumer
        client_id (str): Base client ID for the Kafka consumer
        auto_offset_reset (str): Strategy for handling consumer offset when no committed offset exists.
        enable_auto_commit (bool): Whether to enable automatic offset commits.
                                  Defaults to True
    """
    name: str
    topics: list[str]
    group_id: str
    client_id: str
    auto_offset_reset: str
    enable_auto_commit: bool = True

    def get_consumer_config(self) -> dict[str, Any]:
        """
        Get the Kafka consumer configuration dictionary.
        
        This method generates a complete consumer configuration dictionary suitable
        for use with Kafka consumers. It automatically appends unique UUIDs to the
        client_id and group_id to ensure uniqueness across multiple consumer instances.
        
        Returns:
            dict[str, Any]: A dictionary containing the consumer configuration with:
                - client_id: Original client_id with appended UUID for uniqueness
                - group_id: Original group_id with appended UUID for uniqueness  
                - auto_offset_reset: Strategy for offset reset behavior
                - enable_auto_commit: Auto-commit configuration
        """
        return {
            "client_id": f"{self.client_id}",
            "group_id": f"{self.group_id}",
            "auto_offset_reset": self.auto_offset_reset,  
            "enable_auto_commit": self.enable_auto_commit
        }


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
            config (WorkerConfig): Configuration object containing Kafka connection
                                 details, serialization settings, and other service
                                 configuration parameters
        """
        super().__init__(
            backend=config.get_kafka_backend(),
            title=config.name,
            serializer=EventSerializer(),
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

    def create_stream(self,
                      stream_config: StreamConfig,
                      func: StreamFunc,
                      deserializer: Optional[MiddlewareProtocol] |None = None) -> Stream:
        """
        Create a Kafka stream with the given configuration.
        
        Creates a new Stream object configured with the provided parameters and
        processing function. The stream is configured with event deserialization
        middleware and uses the provided consumer configuration.
        
        Args:
            stream_config (StreamConfig): Configuration object containing all
                                        stream parameters including topics, consumer
                                        group settings, and behavioral options
            func (StreamFunc): The stream processing function that will handle
                             incoming messages. This function should accept the
                             message as its parameter and perform the desired
                             processing logic
            deserializer (Optional[MiddlewareProtocol], optional): Optional deserializer
            
        Returns:
            Stream: A configured Stream object ready to be added to the engine
                   and started for message processing
        """
        middleware_type = middleware.Middleware(deserializer if deserializer is not None else EventDeserializer)

        stream = Stream(
            topics=stream_config.topics,
            name=stream_config.name,
            func=func,
            middlewares=[middleware_type],
            config=stream_config.get_consumer_config(),
            backend=self.backend
        )
        return stream

    def create_and_add_stream(self,
                            name: str,
                            topics: list[str],
                            group_id: str,
                            client_id: str,
                            func: StreamFunc,
                            auto_offset_reset: str,
                            *,
                            deserializer: Optional[MiddlewareProtocol] |None = None,
                            auto_create_topics: bool = True,
                            enable_auto_commit: bool = True) -> Stream:
        """
        Create topics (if needed), create a stream, and add it to the engine.
        
        This is a convenience method that combines topic creation, stream creation,
        and stream registration in a single call. It provides a simple interface
        for the most common use case of setting up a new stream processor.
        
        Args:
            name (str): Unique name for the stream, used for identification and logging
            topics (list[str]): List of Kafka topic names to consume from
            group_id (str): Base consumer group ID for the Kafka consumer. A UUID
                          will be appended for uniqueness
            client_id (str): Base client ID for the Kafka consumer. A UUID will be
                           appended for uniqueness
            func (StreamFunc): Stream processing function that handles incoming messages
            auto_create_topics (bool, optional): Whether to automatically create topics
            auto_offset_reset (str, optional): Consumer offset reset strategy when no
                                             committed offset exists. Defaults to "latest"
            enable_auto_commit (bool, optional): Whether to enable automatic offset
                                               commits. Defaults to True
            
        Returns:
            Stream: The created and registered Stream object, ready for processing
            
        Raises:
            KafkaException: If topic creation fails or stream configuration is invalid
        """
        # Create topics if requested
        if auto_create_topics:
            self.create_topics(topics)

        # Create stream configuration
        stream_config = StreamConfig(
            name=name,
            topics=topics,
            group_id=group_id,
            client_id=client_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=enable_auto_commit
        )

        # Create and add the stream
        stream = self.create_stream(stream_config=stream_config,
                                    func=func,
                                    deserializer=deserializer)
        self.add_stream(stream)

        return stream

    def create_and_add_stream_from_config(self, 
                                        stream_config: StreamConfig, 
                                        func: StreamFunc,
                                        *,
                                        auto_create_topics: bool = True) -> Stream:
        """
        Create a stream from a StreamConfig object and add it to the engine.
        
        This method provides an alternative interface for stream creation when you
        already have a properly configured StreamConfig object. It's useful for
        scenarios where stream configurations are created programmatically or
        loaded from external sources.
        
        Args:
            stream_config (StreamConfig): Pre-configured stream configuration object
                                        containing all necessary parameters for stream
                                        creation including topics, consumer settings,
                                        and behavioral options
            func (StreamFunc): Stream processing function that will handle incoming
                             messages from the configured topics
            auto_create_topics (bool, optional): Whether to automatically create the
                                               topics specified in the stream config
                                               if they don't exist. Defaults to True
            
        Returns:
            Stream: The created and registered Stream object, configured according
                   to the provided StreamConfig and ready for message processing
                   
        Raises:
            KafkaException: If topic creation fails or stream configuration is invalid
        """
        # Create topics if requested
        if auto_create_topics:
            self.create_topics(stream_config.topics)

        # Create and add the stream
        stream = self.create_stream(stream_config, func)
        self.add_stream(stream)

        return stream


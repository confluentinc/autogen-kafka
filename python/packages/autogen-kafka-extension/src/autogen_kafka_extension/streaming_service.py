import uuid
from dataclasses import dataclass

from kstreams import Stream, middleware, StreamEngine, PrometheusMonitor, Consumer, Producer
from kstreams.types import StreamFunc

from autogen_kafka_extension.events.message_serdes import EventSerializer, EventDeserializer
from autogen_kafka_extension.topic_admin import TopicAdmin
from autogen_kafka_extension.worker_config import WorkerConfig


@dataclass
class StreamConfig:
    """Configuration for a Kafka stream."""
    name: str
    topics: list[str]
    group_id: str
    client_id: str
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    
    def get_consumer_config(self) -> dict[str, any]:
        """Get the Kafka consumer configuration dictionary."""
        return {
            "client_id": f"{self.client_id}-{uuid.uuid4()}",
            "group_id": f"{self.group_id}-{uuid.uuid4()}",
            "auto_offset_reset": self.auto_offset_reset,  
            "enable_auto_commit": self.enable_auto_commit
        }


class StreamingService(StreamEngine):
    """
    Kafka streaming engine that extends StreamEngine with topic management capabilities.
    
    This class provides methods to create Kafka topics and streams with proper
    configuration and error handling.
    """
    
    def __init__(self, config: WorkerConfig):
        super().__init__(
            backend=config.get_kafka_backend(),
            title=config.title,
            serializer=EventSerializer(),
            monitor=PrometheusMonitor(),
            consumer_class=Consumer,
            producer_class=Producer,
        )
        self._config = config
        self._topics_admin = TopicAdmin(self._config)

    def create_topics(self, topics: list[str]) -> None:
        """
        Create Kafka topics if they do not already exist.
        
        Args:
            topics: List of topic names to create
        """
        self._topics_admin.create_topics(topic_names=topics)

    def create_stream(self, stream_config: StreamConfig, func: StreamFunc) -> Stream:
        """
        Create a Kafka stream with the given configuration.
        
        Args:
            stream_config: Stream configuration object
            func: Stream processing function
            
        Returns:
            The created Stream object
        """
        stream = Stream(
            topics=stream_config.topics,
            name=stream_config.name,
            func=func,
            middlewares=[middleware.Middleware(EventDeserializer)],
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
                            *,
                            auto_create_topics: bool = True,
                            auto_offset_reset: str = "latest",
                            enable_auto_commit: bool = True) -> Stream:
        """
        Create topics (if needed), create a stream, and add it to the engine.
        
        Args:
            name: Stream name
            topics: List of topics to consume from
            group_id: Kafka consumer group ID
            client_id: Kafka client ID
            func: Stream processing function
            auto_create_topics: Whether to automatically create topics
            auto_offset_reset: Kafka auto offset reset strategy
            enable_auto_commit: Whether to enable auto commit
            
        Returns:
            The created and added Stream object
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
        stream = self.create_stream(stream_config, func)
        self.add_stream(stream)

        return stream

    def create_and_add_stream_from_config(self, 
                                        stream_config: StreamConfig, 
                                        func: StreamFunc,
                                        *,
                                        auto_create_topics: bool = True) -> Stream:
        """
        Create a stream from a StreamConfig object and add it to the engine.
        
        Args:
            stream_config: Stream configuration object
            func: Stream processing function
            auto_create_topics: Whether to automatically create topics
            
        Returns:
            The created and added Stream object
        """
        # Create topics if requested
        if auto_create_topics:
            self.create_topics(stream_config.topics)

        # Create and add the stream
        stream = self.create_stream(stream_config, func)
        self.add_stream(stream)

        return stream


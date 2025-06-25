"""Worker configuration for autogen-kafka-extension.

This module provides configuration classes specifically for Kafka worker runtimes,
including all the topics needed for distributed agent coordination and messaging.
"""
from .service_base_config import ServiceBaseConfig
from .kafka_config import KafkaConfig


class KafkaWorkerConfig(ServiceBaseConfig):
    """Configuration for Kafka worker runtimes.
    
    This class extends the base KafkaConfig with worker-specific settings
    that include all the topics needed for distributed agent coordination:
    - Request/response messaging
    - Agent registry and discovery
    - Subscription management
    - Publishing capabilities
    """
    
    def __init__(
        self,
            kafka_config: KafkaConfig,
        *,
        request_topic: str = "worker_requests",
        response_topic: str = "worker_responses", 
        registry_topic: str = "agent_registry",
        subscription_topic: str = "agent_subscriptions",
        publish_topic: str = "agent_publishes",
    ) -> None:
        """Initialize the Kafka worker configuration.
        
        Args:
            kafka_config: The base Kafka configuration to inherit from.
            request_topic: The Kafka topic name for consuming incoming requests.
            response_topic: The Kafka topic name for publishing response messages.
            registry_topic: The Kafka topic name for agent registry operations.
            subscription_topic: The Kafka topic name for publishing subscription messages.
            publish_topic: The Kafka topic name for publishing messages.

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        super().__init__(kafka_config=kafka_config)

        self._request_topic = request_topic
        self._response_topic = response_topic
        self._registry_topic = registry_topic
        self._subscription_topic = subscription_topic
        self._publish_topic = publish_topic
    
    @property
    def request_topic(self) -> str:
        """Get the Kafka topic to consume messages from."""
        return self._request_topic
    
    @property
    def response_topic(self) -> str:
        """Get the Kafka topic to produce responses to."""
        return self._response_topic
    
    @property
    def registry_topic(self) -> str:
        """Get the Kafka topic for registry messages."""
        return self._registry_topic
    
    @property
    def subscription_topic(self) -> str:
        """Get the Kafka topic for subscription messages."""
        return self._subscription_topic
    
    @property
    def publish_topic(self) -> str:
        """Get the Kafka topic to produce messages to."""
        return self._publish_topic
    
    def get_all_topics(self) -> list[str]:
        """Get all topics used by this worker configuration.
        
        Returns:
            A list of all topic names used by this worker.
        """
        return [
            self._request_topic,
            self._response_topic,
            self._registry_topic,
            self._subscription_topic,
            self._publish_topic,
        ]
    
    def validate(self) -> None:
        """Validate the worker configuration parameters.
        
        Raises:
            ValueError: If any configuration parameters are invalid.
        """
        # Call parent validation
        super().validate()
        
        # Validate worker-specific settings
        topics = {
            "request_topic": self._request_topic,
            "response_topic": self._response_topic,
            "registry_topic": self._registry_topic,
            "subscription_topic": self._subscription_topic,
            "publish_topic": self._publish_topic,
        }
        
        # Check that all topics are non-empty
        for topic_name, topic_value in topics.items():
            if not topic_value or not topic_value.strip():
                raise ValueError(f"{topic_name} cannot be empty")
        
        # Check that all topics are unique
        topic_values = list(topics.values())
        if len(set(topic_values)) != len(topic_values):
            raise ValueError("All worker topics must be unique")
        
        self._validated = True 
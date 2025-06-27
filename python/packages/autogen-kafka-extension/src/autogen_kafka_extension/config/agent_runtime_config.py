"""Worker configuration for autogen-kafka-extension.

This module provides configuration classes specifically for Kafka worker runtimes,
including all the topics needed for distributed agent coordination and messaging.
"""
from typing import Any, Dict
from .service_base_config import ServiceBaseConfig
from .base_config import ValidationResult
from .auto_validate import auto_validate_after_init
from .kafka_config import KafkaConfig


@auto_validate_after_init
class KafkaAgentRuntimeConfig(ServiceBaseConfig):
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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KafkaAgentRuntimeConfig':
        """Create a KafkaWorkerConfig instance from a dictionary.
        
        Args:
            data: Dictionary containing configuration parameters.
            Expected structure:
            {
                'kafka': {
                    'name': str,
                    'group_id': str,
                    'client_id': str,
                    'bootstrap_servers': list[str] or str,
                    'schema_registry': {
                        'url': str,
                        'username': str (optional),
                        'password': str (optional)
                    },
                    ... (other kafka config parameters)
                },
                'worker': {
                    'request_topic': str (optional, default='worker_requests'),
                    'response_topic': str (optional, default='worker_responses'),
                    'registry_topic': str (optional, default='agent_registry'),
                    'subscription_topic': str (optional, default='agent_subscriptions'),
                    'publish_topic': str (optional, default='agent_publishes')
                }
            }
            
        Returns:
            KafkaWorkerConfig instance.
            
        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        # Extract kafka configuration
        kafka_data = data.get(KafkaConfig.config_key(), {})
        if not kafka_data:
            raise ValueError(f"'{KafkaConfig.config_key()}' configuration is required")
        
        # If schema_registry is at the top level (from environment variables), 
        # move it into the kafka_data
        if 'schema_registry' in data and 'schema_registry' not in kafka_data:
            kafka_data['schema_registry'] = data['schema_registry']
        
        kafka_config = KafkaConfig.from_dict(kafka_data)
        
        # Extract runtime-specific configuration
        runtime_data = data.get(cls.config_key(), {})
        
        # Get worker topic names with defaults
        request_topic = runtime_data.get('request_topic', 'worker_requests')
        response_topic = runtime_data.get('response_topic', 'worker_responses')
        registry_topic = runtime_data.get('registry_topic', 'agent_registry')
        subscription_topic = runtime_data.get('subscription_topic', 'agent_subscriptions')
        publish_topic = runtime_data.get('publish_topic', 'agent_publishes')
        
        return cls(
            kafka_config=kafka_config,
            request_topic=request_topic,
            response_topic=response_topic,
            registry_topic=registry_topic,
            subscription_topic=subscription_topic,
            publish_topic=publish_topic
        )

    def _validate_impl(self) -> ValidationResult:
        """Validate the worker configuration parameters."""
        # First get the parent validation result
        parent_result = super()._validate_impl()
        errors = list(parent_result.errors)
        warnings = list(parent_result.warnings) if parent_result.warnings else []
        
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
                errors.append(f"{topic_name} cannot be empty")
        
        # Check that all topics are unique
        topic_values = list(topics.values())
        if len(set(topic_values)) != len(topic_values):
            errors.append("All worker topics must be unique")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def config_key():
        """Return the configuration key for Kafka worker runtime."""
        return 'runtime'
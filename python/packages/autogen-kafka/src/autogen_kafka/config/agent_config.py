"""Agent configuration for autogen-kafka-extension.

This module provides configuration classes specifically for Kafka-based agents,
including request/response topic management and agent-specific settings.
"""
from .service_base_config import ServiceBaseConfig
from .base_config import ValidationResult
from .auto_validate import auto_validate_after_init
from .kafka_config import KafkaConfig
from typing import Dict, Any


@auto_validate_after_init
class KafkaAgentConfig(ServiceBaseConfig):
    """Configuration for Kafka-based agents.
    
    This class extends the base KafkaConfig with agent-specific settings
    such as request and response topics, and agent lifecycle management.
    """
    
    def __init__(
        self,
        kafka_config: KafkaConfig,
        *,
        request_topic: str = "agent_request",
        response_topic: str = "agent_response",
    ) -> None:
        """Initialize the Kafka agent configuration.
        
        Args:
            kafka_config: The Kafka configuration to use for this agent.
            request_topic: The Kafka topic used for sending requests to the agent.
            response_topic: The Kafka topic used for receiving responses from the agent.

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        super().__init__(kafka_config=kafka_config)

        self._request_topic = request_topic
        self._response_topic = response_topic

    @property
    def request_topic(self) -> str:
        """Get the Kafka topic used for sending requests to the agent."""
        return self._request_topic
    
    @property
    def response_topic(self) -> str:
        """Get the Kafka topic used for receiving responses from the agent."""
        return self._response_topic
    
    def _validate_impl(self) -> ValidationResult:
        """Validate the agent configuration parameters."""
        # First get the parent validation result
        parent_result = super()._validate_impl()
        errors = list(parent_result.errors)
        warnings = list(parent_result.warnings) if parent_result.warnings else []
        
        # Validate agent-specific settings
        if not self._request_topic or not self._request_topic.strip():
            errors.append("request_topic cannot be empty")
        
        if not self._response_topic or not self._response_topic.strip():
            errors.append("response_topic cannot be empty")
        
        # Request and response topics should be different
        if self._request_topic == self._response_topic:
            errors.append("request_topic and response_topic must be different")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KafkaAgentConfig':
        """Create a KafkaAgentConfig instance from a dictionary.
        
        Args:
            data: Dictionary containing configuration parameters.
            Expected structure:
            {
                'kafka': {
                    # KafkaConfig parameters
                },
                'request_topic': str (optional, default='agent_request'),
                'response_topic': str (optional, default='agent_response')
            }
            
        Returns:
            KafkaAgentConfig instance.
            
        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        # Extract Kafka configuration
        kafka_data = data.get(KafkaConfig.config_key(), {})
        if not kafka_data:
            raise ValueError(f"'{KafkaConfig.config_key()}' configuration is required")

        # If schema_registry is at the top level (from environment variables),
        # move it into the kafka_data
        if 'schema_registry' in data and 'schema_registry' not in kafka_data:
            kafka_data['schema_registry'] = data['schema_registry']

        kafka_config = KafkaConfig.from_dict(kafka_data)

        agent_data = data.get(cls.config_key(), {})

        # Extract agent-specific parameters
        request_topic = agent_data.get('request_topic', 'agent_request')
        response_topic = agent_data.get('response_topic', 'agent_response')
        
        return cls(
            kafka_config=kafka_config,
            request_topic=request_topic,
            response_topic=response_topic
        )

    @staticmethod
    def config_key():
        """Return the configuration key for Kafka agents."""
        return 'agent'
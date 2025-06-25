"""Agent configuration for autogen-kafka-extension.

This module provides configuration classes specifically for Kafka-based agents,
including request/response topic management and agent-specific settings.
"""
from .service_base_config import ServiceBaseConfig
from .kafka_config import KafkaConfig


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
    
    def validate(self) -> None:
        """Validate the agent configuration parameters.
        
        Raises:
            ValueError: If any configuration parameters are invalid.
        """
        # Call parent validation
        super().validate()
        
        # Validate agent-specific settings
        if not self._request_topic or not self._request_topic.strip():
            raise ValueError("request_topic cannot be empty")
        
        if not self._response_topic or not self._response_topic.strip():
            raise ValueError("response_topic cannot be empty")
        
        # Request and response topics should be different
        if self._request_topic == self._response_topic:
            raise ValueError("request_topic and response_topic must be different")
        
        self._validated = True 
"""Agent configuration for autogen-kafka-extension.

This module provides configuration classes specifically for Kafka-based agents,
including request/response topic management and agent-specific settings.
"""

from typing import Optional
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

from .kafka_config import KafkaConfig
from .schema_registry import SchemaRegistryConfig


class KafkaAgentConfig(KafkaConfig):
    """Configuration for Kafka-based agents.
    
    This class extends the base KafkaConfig with agent-specific settings
    such as request and response topics, and agent lifecycle management.
    """
    
    def __init__(
        self,
        name: str,
        group_id: str,
        client_id: str,
        bootstrap_servers: list[str],
        schema_registry_config: SchemaRegistryConfig,
        *,
        request_topic: str = "agent_request",
        response_topic: str = "agent_response",
        num_partitions: int = 3,
        replication_factor: int = 1,
        auto_offset_reset: str = 'latest',
        security_protocol: Optional[SecurityProtocol] = None,
        security_mechanism: Optional[SaslMechanism] = None,
        sasl_plain_username: Optional[str] = None,
        sasl_plain_password: Optional[str] = None,
    ) -> None:
        """Initialize the Kafka agent configuration.
        
        Args:
            name: A descriptive name for this agent configuration.
            group_id: The Kafka consumer group ID for coordinating message consumption.
            client_id: A unique identifier for this Kafka client instance.
            bootstrap_servers: List of Kafka broker addresses in 'host:port' format.
            schema_registry_config: Configuration for the schema registry service.
            request_topic: The Kafka topic used for sending requests to the agent.
            response_topic: The Kafka topic used for receiving responses from the agent.
            num_partitions: Number of partitions for topics. Defaults to 3.
            replication_factor: Replication factor for topics. Defaults to 1.
            auto_offset_reset: The auto offset reset policy. Defaults to 'latest'.
            security_protocol: Security protocol for Kafka connection.
            security_mechanism: SASL mechanism for authentication.
            sasl_plain_username: Username for SASL PLAIN authentication.
            sasl_plain_password: Password for SASL PLAIN authentication.
            
        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        super().__init__(
            name=name,
            group_id=group_id,
            client_id=client_id,
            bootstrap_servers=bootstrap_servers,
            schema_registry_config=schema_registry_config,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            is_compacted=False,  # Agents typically don't need compacted topics
            auto_offset_reset=auto_offset_reset,
            security_protocol=security_protocol,
            security_mechanism=security_mechanism,
            sasl_plain_username=sasl_plain_username,
            sasl_plain_password=sasl_plain_password,
        )
        
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
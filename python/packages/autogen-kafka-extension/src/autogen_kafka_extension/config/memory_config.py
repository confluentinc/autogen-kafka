"""Memory configuration for autogen-kafka-extension.

This module provides configuration classes specifically for Kafka-based memory
management, including memory topic settings and persistence configuration.
"""

from typing import Optional
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

from .kafka_config import KafkaConfig
from .schema_registry import SchemaRegistryConfig


class KafkaMemoryConfig(KafkaConfig):
    """Configuration for Kafka-based memory management.
    
    This class extends the base KafkaConfig with memory-specific settings
    such as memory topic configuration and persistence behavior.
    
    Memory configurations have specific requirements:
    - Single partition for ordered message processing
    - Early offset reset to rebuild memory from history
    - No compaction to preserve all memory events
    """
    
    def __init__(
        self,
        name: str,
        group_id: str,
        client_id: str,
        bootstrap_servers: list[str],
        schema_registry_config: SchemaRegistryConfig,
        *,
        memory_topic: str = "memory",
        replication_factor: int = 1,
        security_protocol: Optional[SecurityProtocol] = None,
        security_mechanism: Optional[SaslMechanism] = None,
        sasl_plain_username: Optional[str] = None,
        sasl_plain_password: Optional[str] = None,
    ) -> None:
        """Initialize the Kafka memory configuration.
        
        Args:
            name: A descriptive name for this memory configuration.
            group_id: The Kafka consumer group ID for coordinating message consumption.
            client_id: A unique identifier for this Kafka client instance.
            bootstrap_servers: List of Kafka broker addresses in 'host:port' format.
            schema_registry_config: Configuration for the schema registry service.
            memory_topic: The Kafka topic used for memory management.
            replication_factor: Replication factor for topics. Defaults to 1.
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
            num_partitions=1,  # Single partition for ordered processing
            replication_factor=replication_factor,
            is_compacted=False,  # Don't compact memory topics to preserve history
            auto_offset_reset="earliest",  # Start from earliest to rebuild memory
            security_protocol=security_protocol,
            security_mechanism=security_mechanism,
            sasl_plain_username=sasl_plain_username,
            sasl_plain_password=sasl_plain_password,
        )
        
        self._memory_topic = memory_topic
    
    @property
    def memory_topic(self) -> str:
        """Get the Kafka topic used for memory management.
        
        This topic is where memory-related messages will be published and consumed
        for distributed memory synchronization.
        """
        return self._memory_topic
    
    def validate(self) -> None:
        """Validate the memory configuration parameters.
        
        Raises:
            ValueError: If any configuration parameters are invalid.
        """
        # Call parent validation
        super().validate()
        
        # Validate memory-specific settings
        if not self._memory_topic or not self._memory_topic.strip():
            raise ValueError("memory_topic cannot be empty")
        
        # Memory topics should always be single partition
        if self.num_partitions != 1:
            raise ValueError("Memory topics must have exactly 1 partition for ordered processing")
        
        # Memory topics should start from earliest for reconstruction
        if self.auto_offset_reset != "earliest":
            raise ValueError("Memory topics must use 'earliest' offset reset for proper reconstruction")
        
        self._validated = True 
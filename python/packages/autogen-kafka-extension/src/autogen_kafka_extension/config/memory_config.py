"""Memory configuration for autogen-kafka-extension.

This module provides configuration classes specifically for Kafka-based memory
management, including memory topic settings and persistence configuration.
"""
from typing import Optional

from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

from .service_base_config import ServiceBaseConfig
from .schema_registry_config import SchemaRegistryConfig
from .kafka_config import KafkaConfig


class KafkaMemoryConfig(ServiceBaseConfig):
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
        auto_offset_reset: str = "earliest", # Ensure we start from the beginning to rebuild memory
        num_partitions: int = 1,
        replication_factor: int = 1,
        is_compacted: bool = False,
        security_protocol: Optional[SecurityProtocol] = None,
        security_mechanism: Optional[SaslMechanism] = None,
        sasl_plain_username: Optional[str] = None,
        sasl_plain_password: Optional[str] = None,
        memory_topic: str = "memory",
    ) -> None:
        """Initialize the Kafka memory configuration.
        
        Args:
            kafka_config: The Kafka configuration to use for this memory.
            memory_topic: The Kafka topic used for memory management.

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        super().__init__(
            kafka_config=KafkaConfig(
                name=name,
                group_id=group_id,
                client_id=client_id,
                bootstrap_servers=bootstrap_servers,
                schema_registry_config=schema_registry_config,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                is_compacted=is_compacted,
                security_protocol=security_protocol,
                security_mechanism=security_mechanism,
                sasl_plain_username=sasl_plain_username,
                sasl_plain_password=sasl_plain_password,
                auto_offset_reset=auto_offset_reset,
            )
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

        self._validated = True 
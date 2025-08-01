"""Memory configuration for autogen-kafka-extension.

This module provides configuration classes specifically for Kafka-based memory
management, including memory topic settings and persistence configuration.
"""
from typing import Any, Dict

from .service_base_config import ServiceBaseConfig  
from .base_config import ValidationResult
from .auto_validate import auto_validate_after_init
from .schema_registry_config import SchemaRegistryConfig
from .kafka_config import KafkaConfig


@auto_validate_after_init
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
        security_protocol: str|None = None,
        security_mechanism: str|None = None,
        sasl_plain_username: str|None = None,
        sasl_plain_password: str|None = None,
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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KafkaMemoryConfig':
        """Create a KafkaMemoryConfig instance from a dictionary.
        
        Args:
            data: Dictionary containing configuration parameters.
            Expected structure (can handle both flat and nested formats):
            {
                'name': str,
                'group_id': str,
                'client_id': str,
                'bootstrap_servers': list[str] or str,
                'schema_registry': {
                    'url': str,
                    'username': str (optional),
                    'password': str (optional)
                },
                'memory': {
                    'memory_topic': str (optional, default='memory')
                },
                'num_partitions': int (optional, default=1),
                'replication_factor': int (optional, default=1),
                'is_compacted': bool (optional, default=False),
                'auto_offset_reset': str (optional, default='earliest'),
                'security_protocol': str (optional),
                'security_mechanism': str (optional),
                'sasl_plain_username': str (optional),
                'sasl_plain_password': str (optional)
            }
            
        Returns:
            KafkaMemoryConfig instance.
            
        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        # Extract required parameters
        kafka_data = data.get(KafkaConfig.config_key(), {})
        if not kafka_data:
            raise ValueError(f"'{KafkaConfig.config_key()}' configuration is required")

        # If schema_registry is at the top level (from environment variables),
        # move it into the kafka_data
        if 'schema_registry' in data and 'schema_registry' not in kafka_data:
            kafka_data['schema_registry'] = data['schema_registry']

        kafka_config = KafkaConfig.from_dict(kafka_data)

        # Extract memory-specific configuration
        memory_data = data.get('memory', {})
        memory_topic = memory_data.get('memory_topic', 'memory')
        
        return cls(
            name=kafka_config.name,
            group_id=kafka_config.group_id,
            client_id=kafka_config.client_id,
            bootstrap_servers=kafka_config.bootstrap_servers,
            schema_registry_config=kafka_config.schema_registry_config,
            memory_topic=memory_topic,
            num_partitions=kafka_config.num_partitions,
            replication_factor=kafka_config.replication_factor,
            is_compacted=kafka_config.is_compacted,
            auto_offset_reset="earliest",  # Memory should always start from the earliest
            security_protocol=kafka_config.security_protocol,
            security_mechanism=kafka_config.security_mechanism,
            sasl_plain_username=kafka_config.sasl_plain_username,
            sasl_plain_password=kafka_config.sasl_plain_password
        )
    
    def _validate_impl(self) -> ValidationResult:
        """Validate the memory configuration parameters."""
        # First get the parent validation result
        parent_result = super()._validate_impl()
        errors = list(parent_result.errors)
        warnings = list(parent_result.warnings) if parent_result.warnings else []
        
        # Validate memory-specific settings
        if not self._memory_topic or not self._memory_topic.strip():
            errors.append("memory_topic cannot be empty")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def config_key():
        """Return the configuration key for Kafka memory."""
        return 'memory'
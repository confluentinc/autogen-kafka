"""Memory configuration for autogen-kafka-extension.

This module provides configuration classes specifically for Kafka-based memory
management, including memory topic settings and persistence configuration.
"""
from typing import Any, Dict, Optional

from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

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
        name = data.get('name')
        if not name:
            raise ValueError("'name' is required in configuration")
            
        group_id = data.get('group_id')
        if not group_id:
            raise ValueError("'group_id' is required in configuration")
            
        client_id = data.get('client_id')
        if not client_id:
            raise ValueError("'client_id' is required in configuration")
        
        # Handle bootstrap_servers - can be string or list
        bootstrap_servers = data.get('bootstrap_servers')
        if not bootstrap_servers:
            raise ValueError("'bootstrap_servers' is required in configuration")
        
        if isinstance(bootstrap_servers, str):
            bootstrap_servers = [server.strip() for server in bootstrap_servers.split(',')]
        
        # Create schema registry config
        schema_registry_data = data.get('schema_registry', {})
        if not schema_registry_data.get('url'):
            raise ValueError("'schema_registry.url' is required in configuration")
            
        schema_registry_config = SchemaRegistryConfig.from_dict(schema_registry_data)
        
        # Extract memory-specific configuration
        memory_data = data.get('memory', {})
        memory_topic = memory_data.get('memory_topic', 'memory')
        
        # Extract optional parameters with memory-specific defaults
        num_partitions = data.get('num_partitions', 1)  # Memory should have single partition
        replication_factor = data.get('replication_factor', 1)
        is_compacted = data.get('is_compacted', False)  # Memory should not be compacted
        auto_offset_reset = data.get('auto_offset_reset', 'earliest')  # Memory should start from beginning
        
        # Handle security settings
        security_protocol = None
        if data.get('security_protocol'):
            security_protocol = SecurityProtocol(data['security_protocol'])
            
        security_mechanism = None
        if data.get('security_mechanism'):
            security_mechanism = SaslMechanism(data['security_mechanism'])
        
        sasl_plain_username = data.get('sasl_plain_username')
        sasl_plain_password = data.get('sasl_plain_password')
        
        return cls(
            name=name,
            group_id=group_id,
            client_id=client_id,
            bootstrap_servers=bootstrap_servers,
            schema_registry_config=schema_registry_config,
            memory_topic=memory_topic,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            is_compacted=is_compacted,
            auto_offset_reset=auto_offset_reset,
            security_protocol=security_protocol,
            security_mechanism=security_mechanism,
            sasl_plain_username=sasl_plain_username,
            sasl_plain_password=sasl_plain_password
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
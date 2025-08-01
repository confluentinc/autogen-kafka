"""Core Kafka configuration for autogen-kafka-extension.

This module provides the main Kafka configuration class that combines
connection settings, schema registry configuration, and administrative
capabilities in a consolidated interface.
"""
from typing import Optional

from .schema_registry_config import SchemaRegistryConfig
from .base_config import BaseConfig, ValidationResult
from .auto_validate import auto_validate_after_init
from typing import Dict, Any

from .services.kafka_utils import KafkaUtils


@auto_validate_after_init
class KafkaConfig(BaseConfig):
    """Core Kafka configuration with schema registry and administrative capabilities.
    
    This class provides a comprehensive Kafka configuration that includes:
    - Basic Kafka connection settings
    - Schema registry integration
    - Administrative client configuration
    - Topic management settings
    - Security and authentication settings
    """
    
    def __init__(
        self,
        name: str,
        group_id: str,
        client_id: str,
        bootstrap_servers: list[str],
        schema_registry_config: SchemaRegistryConfig,
        *,
        num_partitions: int = 3,
        replication_factor: int = 1,
        is_compacted: bool = False,
        auto_offset_reset: str = 'latest',
        security_protocol: str = "PLAINTEXT",
        security_mechanism: str = "PLAIN",
        sasl_plain_username: str | None = None,
        sasl_plain_password: str | None = None,
        enable_auto_commit: bool = True,
    ) -> None:
        """Initialize the Kafka configuration.
        
        Args:
            name: A descriptive name for this configuration.
            group_id: The Kafka consumer group ID for coordinating message consumption.
            client_id: A unique identifier for this Kafka client instance.
            bootstrap_servers: List of Kafka broker addresses in 'host:port' format.
            schema_registry_config: Configuration for the schema registry service.
            num_partitions: Number of partitions for topics. Defaults to 3.
            replication_factor: Replication factor for topics. Defaults to 1.
            is_compacted: Whether topics should be compacted. Defaults to False.
            auto_offset_reset: The auto offset reset policy. Defaults to 'latest'.
            security_protocol: Security protocol for Kafka connection.
            security_mechanism: SASL mechanism for authentication.
            sasl_plain_username: Username for SASL PLAIN authentication.
            sasl_plain_password: Password for SASL PLAIN authentication.
            
        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        super().__init__()

        if not name or not name.strip():
            raise ValueError("Configuration name cannot be empty")

        self._name = name.strip()
        self._group_id = group_id
        self._client_id = client_id
        self._bootstrap_servers = bootstrap_servers
        self._security_protocol = security_protocol
        self._security_mechanism = security_mechanism
        self._sasl_plain_username = sasl_plain_username
        self._sasl_plain_password = sasl_plain_password
        self._schema_registry_config = schema_registry_config
        self._num_partitions = num_partitions
        self._replication_factor = replication_factor
        self._is_compacted = is_compacted
        self._auto_offset_reset = auto_offset_reset
        self._enable_auto_commit = enable_auto_commit

        # Lazy initialization for services
        self._utils : KafkaUtils | None = None

    @property
    def name(self) -> str:
        """Get the configuration name.

        Returns:
            The descriptive name of this configuration.
        """
        return self._name

    @property
    def schema_registry_config(self) -> SchemaRegistryConfig:
        """Get the schema registry configuration."""
        return self._schema_registry_config
    
    @property
    def num_partitions(self) -> int:
        """Get the number of partitions for topics."""
        return self._num_partitions
    
    @property
    def replication_factor(self) -> int:
        """Get the replication factor for topics."""
        return self._replication_factor
    
    @property
    def is_compacted(self) -> bool:
        """Check if topics should be compacted."""
        return self._is_compacted
    
    @property
    def auto_offset_reset(self) -> str:
        """Get the auto offset reset policy."""
        return self._auto_offset_reset

    @property
    def group_id(self) -> str:
        """Get the Kafka consumer group ID."""
        return self._group_id

    @property
    def client_id(self) -> str:
        """Get the Kafka client ID."""
        return self._client_id

    @property
    def bootstrap_servers(self) -> list[str]:
        """Get the list of Kafka bootstrap servers."""
        return self._bootstrap_servers.copy()

    @property
    def security_protocol(self) -> str:
        """Get the security protocol."""
        return self._security_protocol

    @property
    def security_mechanism(self) -> str:
        """Get the SASL mechanism."""
        return self._security_mechanism

    @property
    def sasl_plain_username(self) -> Optional[str]:
        """Get the SASL username."""
        return self._sasl_plain_username

    @property
    def sasl_plain_password(self) -> Optional[str]:
        """Get the SASL password."""
        return self._sasl_plain_password

    def utils(self) -> KafkaUtils:
        if self._utils is None:
            self._utils = KafkaUtils(bootstrap_servers=self._bootstrap_servers,
                                    security_protocol=self._security_protocol,
                                    security_mechanism=self._security_mechanism,
                                    sasl_plain_password=self._sasl_plain_password,
                                    sasl_plain_username=self._sasl_plain_username,
                                    num_partitions=self._num_partitions,
                                    replication_factor=self._replication_factor,
                                    is_compacted=self._is_compacted,
                                     schema_registry_config=self._schema_registry_config)

        return self._utils

    def _validate_impl(self) -> ValidationResult:
        """Validate the Kafka configuration parameters."""
        errors = []
        warnings = []

        # Validate required string fields
        if not self._group_id or not self._group_id.strip():
            errors.append("group_id cannot be empty")

        if not self._client_id or not self._client_id.strip():
            errors.append("client_id cannot be empty")

        if not self._bootstrap_servers:
            errors.append("bootstrap_servers cannot be empty")

        # Validate bootstrap server format
        for server in self._bootstrap_servers:
            if not server or ':' not in server:
                errors.append(f"Invalid bootstrap server format: {server}")

        # Validate SASL authentication requirements
        if self._security_protocol and self._security_protocol != "PLAINTEXT":
            if self._security_mechanism == "PLAIN":
                if not self._sasl_plain_username or not self._sasl_plain_password:
                    errors.append("SASL PLAIN authentication requires both username and password")

        # Validate topic settings
        if self._num_partitions < 1:
            errors.append("num_partitions must be at least 1")
        
        if self._replication_factor < 1:
            errors.append("replication_factor must be at least 1")
        
        if self._auto_offset_reset not in ['earliest', 'latest', 'none']:
            errors.append("auto_offset_reset must be one of: 'earliest', 'latest', 'none'")
        
        # Validate schema registry config
        if not self._schema_registry_config:
            errors.append("schema_registry_config is required")
        else:
            # Validate the schema registry config as well
            try:
                schema_result = self._schema_registry_config.validate()
                if not schema_result.is_valid:
                    errors.extend([f"Schema Registry: {error}" for error in schema_result.errors])
                if schema_result.warnings:
                    warnings.extend([f"Schema Registry: {warning}" for warning in schema_result.warnings])
            except Exception as e:
                errors.append(f"Schema Registry validation failed: {e}")

        # Add warnings for common configuration issues
        if self._replication_factor == 1:
            warnings.append("Replication factor of 1 provides no fault tolerance")
        
        if self._num_partitions == 1:
            warnings.append("Single partition may limit throughput")
        
        if self._security_protocol == "PLAINTEXT":
            warnings.append("Using PLAINTEXT security protocol - consider using SSL/SASL for production")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KafkaConfig':
        """Create a KafkaConfig instance from a dictionary.
        
        Args:
            data: Dictionary containing configuration parameters.
            Expected structure:
            {
                'name': str,
                'group_id': str,
                'client_id': str,
                'bootstrap_servers': list[str] or str (comma-separated),
                'schema_registry': {
                    'url': str,
                    'username': str (optional),
                    'password': str (optional)
                },
                'num_partitions': int (optional, default=3),
                'replication_factor': int (optional, default=1),
                'is_compacted': bool (optional, default=False),
                'auto_offset_reset': str (optional, default='latest'),
                'security_protocol': str (optional),
                'security_mechanism': str (optional),
                'sasl_plain_username': str (optional),
                'sasl_plain_password': str (optional)
            }
            
        Returns:
            KafkaConfig instance.
            
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
        schema_registry_data = data.get(SchemaRegistryConfig.config_key(), {})
        if not schema_registry_data.get('url'):
            raise ValueError(f"'{SchemaRegistryConfig.config_key()}.url' is required in configuration")
            
        schema_registry_config = SchemaRegistryConfig.from_dict(schema_registry_data)
        
        # Extract optional parameters with defaults
        num_partitions = data.get('num_partitions', 3)
        replication_factor = data.get('replication_factor', 3)
        is_compacted = data.get('is_compacted', False)
        auto_offset_reset = data.get('auto_offset_reset', 'latest')
        
        # Handle security settings
        security_protocol = None
        if data.get('security_protocol'):
            security_protocol = data['security_protocol']
        else:
            security_protocol = "PLAINTEXT"
            
        security_mechanism = None
        if data.get('security_mechanism'):
            security_mechanism = data['security_mechanism']
        else:
            security_mechanism = "PLAIN"
        
        sasl_plain_username = data.get('sasl_plain_username')
        sasl_plain_password = data.get('sasl_plain_password')
        
        return cls(
            name=name,
            group_id=group_id,
            client_id=client_id,
            bootstrap_servers=bootstrap_servers,
            schema_registry_config=schema_registry_config,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            is_compacted=is_compacted,
            auto_offset_reset=auto_offset_reset,
            security_protocol=security_protocol,
            security_mechanism=security_mechanism,
            sasl_plain_username=sasl_plain_username,
            sasl_plain_password=sasl_plain_password
        )

    @staticmethod
    def config_key():
        """Return the configuration key for Kafka."""
        return 'kafka'

    def get_consumer_config(self, topic: str) -> Dict[str, Any]:
        return {
            "client.id": self.client_id + f"-{topic}",
            "group.id": self.group_id + f"-{topic}",
            "auto.offset.reset": self.auto_offset_reset,
            "enable.auto.commit": self._enable_auto_commit,
            "bootstrap.servers": ",".join(self.bootstrap_servers),
            "security.protocol": self.security_protocol if self.security_protocol else None,
            "sasl.mechanism": self.security_mechanism if self.security_mechanism else None,
            "sasl.username": self.sasl_plain_username,
            "sasl.password": self.sasl_plain_password
        }

    def get_producer_config(self):
        return {
            "client.id": self.client_id,
            "bootstrap.servers": ",".join(self.bootstrap_servers),
            "security.protocol": self.security_protocol if self.security_protocol else None,
            "sasl.mechanism": self.security_mechanism if self.security_mechanism else None,
            "sasl.username": self.sasl_plain_username,
            "sasl.password": self.sasl_plain_password
        }
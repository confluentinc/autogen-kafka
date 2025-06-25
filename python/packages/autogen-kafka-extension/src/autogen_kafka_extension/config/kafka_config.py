"""Core Kafka configuration for autogen-kafka-extension.

This module provides the main Kafka configuration class that combines
connection settings, schema registry configuration, and administrative
capabilities in a consolidated interface.
"""

from typing import Optional
from aiokafka.helpers import create_ssl_context
from confluent_kafka.admin import AdminClient
from kstreams.backends import Kafka
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

from .schema_registry_config import SchemaRegistryConfig
from .schema_registry_service import SchemaRegistryService
from .base_config import BaseConfig

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
        security_protocol: Optional[SecurityProtocol] = None,
        security_mechanism: Optional[SaslMechanism] = None,
        sasl_plain_username: Optional[str] = None,
        sasl_plain_password: Optional[str] = None,
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

        # Lazy initialization for services
        self._schema_registry_service: Optional[SchemaRegistryService] = None

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
    def security_protocol(self) -> Optional[SecurityProtocol]:
        """Get the security protocol."""
        return self._security_protocol

    @property
    def security_mechanism(self) -> Optional[SaslMechanism]:
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
    
    def get_kafka_backend(self) -> Kafka:
        """Create and configure a Kafka backend instance for streaming operations.
        
        This method creates a kstreams Kafka backend configured with all the
        security and connection settings from this configuration. The backend
        can be used for creating producers, consumers, and streaming applications.
        
        Returns:
            A configured Kafka backend instance ready for streaming operations.
            
        Note:
            The SSL context is automatically created if security protocols require it.
        """
        return Kafka(
            bootstrap_servers=self._bootstrap_servers,
            security_protocol=self._security_protocol or SecurityProtocol.PLAINTEXT,
            sasl_mechanism=self._security_mechanism or SaslMechanism.PLAIN,
            sasl_plain_username=self._sasl_plain_username,
            sasl_plain_password=self._sasl_plain_password,
            ssl_context=create_ssl_context(),
        )

    def get_schema_registry_service(self) -> SchemaRegistryService:
        """Get the schema registry service instance.
        
        This method returns a SchemaRegistryService configured with the
        schema registry URL and optional authentication credentials. The service
        is lazily initialized and cached for reuse.
        
        Returns:
            A configured SchemaRegistryService instance.
        """
        if self._schema_registry_service is None:
            self._schema_registry_service = SchemaRegistryService(
                config=self._schema_registry_config
            )
        return self._schema_registry_service
    
    def get_admin_client(self) -> AdminClient:
        """Create and configure a Kafka AdminClient for administrative operations.
        
        This method creates a confluent-kafka AdminClient configured with the
        configuration's connection and security settings. The admin client can be
        used for topic management, cluster metadata operations, and other
        administrative tasks.
        
        Returns:
            A configured Kafka AdminClient instance for administrative operations.
            
        Note:
            - Default values are provided for client.id and group.id if not configured
            - Security settings default to PLAINTEXT and PLAIN if not specified
            - None values for SASL credentials are handled appropriately
        """
        config = {
            'bootstrap.servers': ','.join(self._bootstrap_servers),
            'client.id': self._client_id or 'autogen-kafka-extension',
            'group.id': self._group_id or 'autogen-kafka-extension-group',
            'security.protocol': (
                self._security_protocol.value 
                if self._security_protocol 
                else SecurityProtocol.PLAINTEXT.value
            ),
            'sasl.mechanism': (
                self._security_mechanism.value 
                if self._security_mechanism 
                else SaslMechanism.PLAIN.value
            ),
        }
        
        # Only add SASL credentials if they are provided
        if self._sasl_plain_username:
            config['sasl.username'] = self._sasl_plain_username
        if self._sasl_plain_password:
            config['sasl.password'] = self._sasl_plain_password
        
        return AdminClient(conf=config)
    
    def validate(self) -> None:
        """Validate the Kafka configuration parameters.
        
        Raises:
            ValueError: If any configuration parameters are invalid.
        """
        if not self._group_id or not self._group_id.strip():
            raise ValueError("group_id cannot be empty")

        if not self._client_id or not self._client_id.strip():
            raise ValueError("client_id cannot be empty")

        if not self._bootstrap_servers:
            raise ValueError("bootstrap_servers cannot be empty")

        # Validate bootstrap server format
        for server in self._bootstrap_servers:
            if not server or ':' not in server:
                raise ValueError(f"Invalid bootstrap server format: {server}")

        # Validate SASL authentication requirements
        if self._security_protocol and self._security_protocol != SecurityProtocol.PLAINTEXT:
            if self._security_mechanism == SaslMechanism.PLAIN:
                if not self._sasl_plain_username or not self._sasl_plain_password:
                    raise ValueError(
                        "SASL PLAIN authentication requires both username and password"
                    )

        self._validated = True

        # Validate topic settings
        if self._num_partitions < 1:
            raise ValueError("num_partitions must be at least 1")
        
        if self._replication_factor < 1:
            raise ValueError("replication_factor must be at least 1")
        
        if self._auto_offset_reset not in ['earliest', 'latest', 'none']:
            raise ValueError(
                "auto_offset_reset must be one of: 'earliest', 'latest', 'none'"
            )
        
        # Validate schema registry config
        if not self._schema_registry_config:
            raise ValueError("schema_registry_config is required")
        
        self._validated = True 
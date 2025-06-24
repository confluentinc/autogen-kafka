"""Base configuration class for all autogen-kafka-extension configurations.

This module provides the abstract base class that defines common patterns
and validation logic used across all configuration classes in the extension.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism


class BaseConfig(ABC):
    """Abstract base class for all configuration objects.
    
    This class defines the common interface and validation patterns used
    across all configuration classes in the autogen-kafka-extension.
    It provides basic validation, common properties, and ensures consistency
    in configuration handling.
    
    Subclasses must implement the validate() method to provide specific
    validation logic for their configuration parameters.
    """
    
    def __init__(self, name: str) -> None:
        """Initialize the base configuration.
        
        Args:
            name: A descriptive name for this configuration instance.
            
        Raises:
            ValueError: If the name is empty or None.
        """
        if not name or not name.strip():
            raise ValueError("Configuration name cannot be empty")
        
        self._name = name.strip()
        self._validated = False
    
    @property
    def name(self) -> str:
        """Get the configuration name.
        
        Returns:
            The descriptive name of this configuration.
        """
        return self._name
    
    @property 
    def is_validated(self) -> bool:
        """Check if this configuration has been validated.
        
        Returns:
            True if validate() has been called successfully, False otherwise.
        """
        return self._validated
    
    @abstractmethod
    def validate(self) -> None:
        """Validate the configuration parameters.
        
        This method should check all configuration parameters for validity
        and raise appropriate exceptions if any issues are found.
        
        Raises:
            ValueError: If any configuration parameters are invalid.
            TypeError: If any parameters have incorrect types.
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary representation.
        
        Returns:
            A dictionary containing all public configuration parameters.
            Private attributes (starting with _) are excluded.
        """
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if hasattr(value, 'to_dict'):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
        return result
    
    def __repr__(self) -> str:
        """Return string representation of the configuration."""
        return f"{self.__class__.__name__}(name='{self.name}')"


class KafkaBaseConfig(BaseConfig):
    """Base configuration for Kafka-related settings.
    
    This class provides common Kafka configuration parameters and validation
    logic used by all Kafka-based components in the extension.
    """
    
    def __init__(
        self,
        name: str,
        group_id: str,
        client_id: str,
        bootstrap_servers: list[str],
        *,
        security_protocol: Optional[SecurityProtocol] = None,
        security_mechanism: Optional[SaslMechanism] = None,
        sasl_plain_username: Optional[str] = None,
        sasl_plain_password: Optional[str] = None,
    ) -> None:
        """Initialize Kafka base configuration.
        
        Args:
            name: Descriptive name for this configuration.
            group_id: Kafka consumer group ID.
            client_id: Unique identifier for this Kafka client.
            bootstrap_servers: List of Kafka broker addresses.
            security_protocol: Security protocol for Kafka connection.
            security_mechanism: SASL mechanism for authentication.
            sasl_plain_username: Username for SASL PLAIN authentication.
            sasl_plain_password: Password for SASL PLAIN authentication.
            
        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        super().__init__(name)
        
        self._group_id = group_id
        self._client_id = client_id
        self._bootstrap_servers = bootstrap_servers
        self._security_protocol = security_protocol
        self._security_mechanism = security_mechanism
        self._sasl_plain_username = sasl_plain_username
        self._sasl_plain_password = sasl_plain_password
    
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
    
    def validate(self) -> None:
        """Validate Kafka configuration parameters.
        
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
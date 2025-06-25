"""Schema Registry configuration and service for autogen-kafka-extension.

This module provides Schema Registry configuration and service classes
that are used by Kafka configurations for serialization/deserialization.
"""

from typing import Dict, Optional
import logging

from .base_config import BaseConfig

logger = logging.getLogger(__name__)

class SchemaRegistryConfig(BaseConfig):
    """Configuration for Schema Registry."""

    def __init__(self, url: str = "http://localhost:8081", api_key: Optional[str] = None,
                 api_secret: Optional[str] = None, ssl_ca_location: Optional[str] = None,
                 ssl_cert_location: Optional[str] = None, ssl_key_location: Optional[str] = None):
        super().__init__()
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.ssl_ca_location = ssl_ca_location
        self.ssl_cert_location = ssl_cert_location
        self.ssl_key_location = ssl_key_location

    def to_dict(self) -> Dict[str, str]:
        """Convert configuration to dictionary."""
        config = {'url': self.url}

        if self.api_key and self.api_secret:
            config.update({
                'basic.auth.credentials.source': 'USER_INFO',
                'basic.auth.user.info': f'{self.api_key}:{self.api_secret}'
            })

        if self.ssl_ca_location:
            config['ssl.ca.location'] = self.ssl_ca_location
        if self.ssl_cert_location:
            config['ssl.certificate.location'] = self.ssl_cert_location
        if self.ssl_key_location:
            config['ssl.key.location'] = self.ssl_key_location

        return config

    def validate(self) -> None:
        super().validate()

        """Validate the configuration."""
        if not self.url:
            raise ValueError("Schema Registry URL must be provided.")
        if self.api_key and not self.api_secret:
            raise ValueError("API key provided without API secret.")
        if self.api_secret and not self.api_key:
            raise ValueError("API secret provided without API key.")
        if self.ssl_ca_location and not (self.ssl_cert_location and self.ssl_key_location):
            raise ValueError("SSL CA location requires both certificate and key locations to be set.")

        self._validated = True


"""Schema Registry configuration and service for autogen-kafka-extension.

This module provides Schema Registry configuration and service classes
that are used by Kafka configurations for serialization/deserialization.
"""

from typing import Dict, Optional
import logging

from .base_config import BaseConfig, ValidationResult
from .auto_validate import auto_validate_after_init

logger = logging.getLogger(__name__)

@auto_validate_after_init
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

    def _validate_impl(self) -> ValidationResult:
        """Validate the Schema Registry configuration."""
        errors = []
        warnings = []

        if not self.url:
            errors.append("Schema Registry URL must be provided.")
        
        if self.api_key and not self.api_secret:
            errors.append("API key provided without API secret.")
        
        if self.api_secret and not self.api_key:
            errors.append("API secret provided without API key.")
        
        if self.ssl_ca_location and not (self.ssl_cert_location and self.ssl_key_location):
            errors.append("SSL CA location requires both certificate and key locations to be set.")

        # Add some warnings for common configuration issues
        if not self.api_key and not self.api_secret:
            warnings.append("No authentication configured for Schema Registry.")
        
        if self.url.startswith("http://") and not self.url.startswith("http://localhost"):
            warnings.append("Using HTTP (not HTTPS) for Schema Registry connection.")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


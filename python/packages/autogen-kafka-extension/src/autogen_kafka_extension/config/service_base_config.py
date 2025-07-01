from abc import ABC
from typing import Optional

from .base_config import BaseConfig, ValidationResult
from .auto_validate import auto_validate_after_init
from .kafka_config import KafkaConfig

@auto_validate_after_init
class ServiceBaseConfig(BaseConfig, ABC):

    def __init__(self, kafka_config: KafkaConfig) -> None:
        """Initialize the base service configuration.

        Args:
            kafka_config: The Kafka configuration to use for this service.

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        super().__init__()
        self._kafka_config = kafka_config

    @property
    def kafka_config(self) -> KafkaConfig:
        """Get the Kafka configuration for this service."""
        return self._kafka_config

    def _validate_impl(self) -> ValidationResult:
        """Validate the service configuration parameters."""
        errors = []
        warnings = []

        # Validate Kafka configuration
        if not self._kafka_config or not isinstance(self._kafka_config, BaseConfig):
            errors.append("Invalid Kafka configuration provided")
        else:
            # Validate the Kafka configuration
            try:
                kafka_result = self._kafka_config.validate()
                if not kafka_result.is_valid:
                    errors.extend([f"Kafka Config: {error}" for error in kafka_result.errors])
                if kafka_result.warnings:
                    warnings.extend([f"Kafka Config: {warning}" for warning in kafka_result.warnings])
            except Exception as e:
                errors.append(f"Kafka configuration validation failed: {e}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


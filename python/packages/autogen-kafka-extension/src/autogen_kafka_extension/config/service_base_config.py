from abc import ABC

from .base_config import BaseConfig
from .kafka_config import KafkaConfig

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

    def validate(self) -> None:
        """Validate the service configuration parameters.

        Raises:
            ValueError: If any configuration parameters are invalid.
        """
        # Call parent validation
        super().validate()

        # Validate Kafka configuration
        if not self._kafka_config or not isinstance(self._kafka_config, BaseConfig):
            raise ValueError("Invalid Kafka configuration provided")

        self._kafka_config.validate()


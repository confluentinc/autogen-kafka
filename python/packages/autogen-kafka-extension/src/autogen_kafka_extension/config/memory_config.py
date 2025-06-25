"""Memory configuration for autogen-kafka-extension.

This module provides configuration classes specifically for Kafka-based memory
management, including memory topic settings and persistence configuration.
"""
from .service_base_config import ServiceBaseConfig
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
        kafka_config: KafkaConfig,
        *,
        memory_topic: str = "memory",
    ) -> None:
        """Initialize the Kafka memory configuration.
        
        Args:
            kafka_config: The Kafka configuration to use for this memory.
            memory_topic: The Kafka topic used for memory management.

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        super().__init__(kafka_config=kafka_config)

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
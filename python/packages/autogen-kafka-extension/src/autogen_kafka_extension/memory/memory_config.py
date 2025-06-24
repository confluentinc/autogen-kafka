"""Memory configuration - compatibility wrapper.

This module provides backward compatibility by wrapping the new consolidated
KafkaMemoryConfig from the config package.
"""

from autogen_kafka_extension.config import KafkaMemoryConfig

# Provide backward compatibility alias - keep the old name for compatibility
MemoryConfig = KafkaMemoryConfig
"""Agent configuration - compatibility wrapper.

This module provides backward compatibility by wrapping the new consolidated
KafkaAgentConfig from the config package.
"""

from autogen_kafka_extension.config import KafkaAgentConfig as _KafkaAgentConfig

# Provide backward compatibility alias
KafkaAgentConfig = _KafkaAgentConfig 
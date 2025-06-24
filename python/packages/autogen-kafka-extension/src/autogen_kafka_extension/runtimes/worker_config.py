"""Worker configuration - compatibility wrapper.

This module provides backward compatibility by wrapping the new consolidated
KafkaWorkerConfig from the config package.
"""

from autogen_kafka_extension.config import KafkaWorkerConfig

# Provide backward compatibility alias - keep the old name for compatibility
WorkerConfig = KafkaWorkerConfig 
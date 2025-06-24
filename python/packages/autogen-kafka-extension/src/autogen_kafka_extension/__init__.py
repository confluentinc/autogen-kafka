"""AutoGen Kafka Extension - Main Package.

This package provides Kafka-based extensions for AutoGen agents, including:
- KafkaStreamingAgent: Kafka-based agent communication
- KafkaMemory: Distributed memory using Kafka
- KafkaWorkerAgentRuntime: Kafka-based agent runtime
- Configuration classes for easy setup
"""

# Configuration classes (import first to avoid circular dependencies)
from .config import (
    BaseConfig,
    SchemaRegistryConfig,
    SchemaRegistryService,
    KafkaConfig,
    KafkaAgentConfig,
    KafkaMemoryConfig,
    KafkaWorkerConfig,
    StreamingServiceConfig,
)

# Essential shared utilities
from .shared import (
    StreamingService,
    StreamingWorkerBase,
    TopicAdminService,
    BackgroundTaskManager,
)

# Core components (import after dependencies)
from .agent import KafkaStreamingAgent
from .memory import KafkaMemory, KafkaMemoryError, TopicDeletionTimeoutError
from .runtimes import KafkaWorkerAgentRuntime, MessagingClient

__version__ = "0.1.0"

__all__ = [
    # Core components
    "KafkaStreamingAgent",
    "KafkaMemory",
    "KafkaMemoryError",
    "TopicDeletionTimeoutError",
    "KafkaWorkerAgentRuntime",
    "MessagingClient",
    
    # Configuration classes
    "BaseConfig",
    "SchemaRegistryConfig",
    "SchemaRegistryService",
    "KafkaConfig",
    "KafkaAgentConfig",
    "KafkaMemoryConfig", 
    "KafkaWorkerConfig",
    "StreamingServiceConfig",
    
    # Shared utilities
    "StreamingService",
    "StreamingWorkerBase",
    "TopicAdminService",
    "BackgroundTaskManager",
]

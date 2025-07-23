"""AutoGen Kafka Extension - Main Package.

This package provides Kafka-based extensions for AutoGen agents, including:
- KafkaStreamingAgent: Kafka-based agent communication
- KafkaMemory: Distributed memory using Kafka
- KafkaWorkerAgentRuntime: Kafka-based agent runtime
- Configuration classes for easy setup
"""

# Configuration classes (import first to avoid circular dependencies)
from .config import (
    SchemaRegistryConfig,
    KafkaAgentConfig,
    KafkaMemoryConfig,
    KafkaAgentRuntimeConfig,
    StreamingServiceConfig,
    BaseConfig,
    KafkaConfig,
    ServiceBaseConfig,
    KafkaUtils,
)

# Essential shared utilities
from .shared import (
    StreamingService,
    StreamingWorkerBase,
    BackgroundTaskManager,
)

# Core components (import after dependencies)
from .agent import KafkaStreamingAgent
from .memory import KafkaMemory, KafkaMemoryError, TopicDeletionTimeoutError
from .runtimes import KafkaAgentRuntime, MessagingClient
from .runtimes.services import SubscriptionService
from .runtimes.kafka_agent_runtime_factory import KafkaAgentRuntimeFactory

__version__ = "0.1.0"

__all__ = [
    # Core components
    "KafkaStreamingAgent",
    "KafkaMemory",
    "KafkaMemoryError",
    "TopicDeletionTimeoutError",
    "KafkaAgentRuntime",
    "MessagingClient",
    "SubscriptionService",
    "KafkaAgentRuntimeFactory",

    # Configuration classes
    "SchemaRegistryConfig",
    "KafkaAgentConfig",
    "KafkaMemoryConfig",
    "KafkaAgentRuntimeConfig",
    "StreamingServiceConfig",
    "ServiceBaseConfig",
    "BaseConfig",
    "KafkaConfig",

    # Shared utilities
    "StreamingService",
    "StreamingWorkerBase",
    "BackgroundTaskManager",
    "KafkaUtils",
]

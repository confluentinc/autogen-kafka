"""Agent package for autogen-kafka-extension.

This package provides Kafka-based agent implementations and configurations.
"""

from .kafka_streaming_agent import KafkaStreamingAgent
from .kafka_agent_config import KafkaAgentConfig  # backward compatibility
from .event import AgentEvent

__all__ = [
    "KafkaStreamingAgent", 
    "KafkaAgentConfig",
    "AgentEvent",
]

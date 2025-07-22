"""Agent package for autogen-kafka-extension.

This package provides Kafka-based agent implementations and configurations.
"""

from .kafka_streaming_agent import KafkaStreamingAgent
from .event import AgentEvent

__all__ = [
    "KafkaStreamingAgent", 
    "AgentEvent",
]

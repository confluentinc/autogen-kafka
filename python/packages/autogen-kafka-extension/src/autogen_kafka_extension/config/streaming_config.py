"""Streaming service configuration for autogen-kafka-extension.

This module provides configuration classes for streaming services,
including consumer configuration and stream processing settings.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class StreamingServiceConfig:
    """Configuration for streaming service components.
    
    This class provides a clean configuration interface for streaming services
    that consume from Kafka topics and process messages with specific types.
    """
    
    name: str
    topic: str
    group_id: str
    client_id: str
    target_type: type
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    auto_create_topics: bool = True
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate the streaming service configuration.
        
        Raises:
            ValueError: If any configuration parameters are invalid.
        """
        if not self.name or not self.name.strip():
            raise ValueError("name cannot be empty")
        
        if not self.topic or not self.topic.strip():
            raise ValueError("topic cannot be empty")
        
        if not self.group_id or not self.group_id.strip():
            raise ValueError("group_id cannot be empty")
        
        if not self.client_id or not self.client_id.strip():
            raise ValueError("client_id cannot be empty")
        
        if not self.target_type:
            raise ValueError("target_type cannot be None")
        
        if self.auto_offset_reset not in ["earliest", "latest", "none"]:
            raise ValueError(
                "auto_offset_reset must be one of: 'earliest', 'latest', 'none'"
            )
    
    def get_consumer_config(self) -> Dict[str, Any]:
        """Get the Kafka consumer configuration dictionary.
        
        This method generates a complete consumer configuration dictionary suitable
        for use with Kafka consumers. It includes all the necessary settings for
        consumer behavior and identification.
        
        Returns:
            A dictionary containing the consumer configuration with:
            - client_id: Client identifier for this consumer
            - group_id: Consumer group identifier
            - auto_offset_reset: Strategy for offset reset behavior
            - enable_auto_commit: Auto-commit configuration
        """
        return {
            "client_id": self.client_id,
            "group_id": self.group_id,
            "auto_offset_reset": self.auto_offset_reset,
            "enable_auto_commit": self.enable_auto_commit,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to a dictionary representation.
        
        Returns:
            A dictionary containing all configuration parameters.
        """
        return {
            "name": self.name,
            "topic": self.topic,
            "group_id": self.group_id,
            "client_id": self.client_id,
            "target_type": self.target_type.__name__ if self.target_type else None,
            "auto_offset_reset": self.auto_offset_reset,
            "enable_auto_commit": self.enable_auto_commit,
            "auto_create_topics": self.auto_create_topics,
        }
    
    def __repr__(self) -> str:
        """Return string representation of the configuration."""
        return (
            f"StreamingServiceConfig("
            f"name='{self.name}', "
            f"topic='{self.topic}', "
            f"group_id='{self.group_id}', "
            f"client_id='{self.client_id}'"
            f")"
        ) 
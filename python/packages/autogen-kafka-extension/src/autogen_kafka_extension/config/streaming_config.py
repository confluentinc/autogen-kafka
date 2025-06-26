"""Streaming service configuration for autogen-kafka-extension.

This module provides configuration classes for streaming services,
including consumer configuration and stream processing settings.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
from pathlib import Path
from .config_loader import ConfigLoader


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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StreamingServiceConfig':
        """Create a StreamingServiceConfig instance from a dictionary.
        
        Args:
            data: Dictionary containing configuration parameters.
            Expected structure:
            {
                'name': str,
                'topic': str,
                'group_id': str,
                'client_id': str,
                'target_type': str (class name),
                'auto_offset_reset': str (optional, default='latest'),
                'enable_auto_commit': bool (optional, default=True),
                'auto_create_topics': bool (optional, default=True)
            }
            
        Returns:
            StreamingServiceConfig instance.
            
        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        # Extract required parameters
        name = data.get('name')
        if not name:
            raise ValueError("'name' is required in configuration")
            
        topic = data.get('topic')
        if not topic:
            raise ValueError("'topic' is required in configuration")
            
        group_id = data.get('group_id')
        if not group_id:
            raise ValueError("'group_id' is required in configuration")
            
        client_id = data.get('client_id')
        if not client_id:
            raise ValueError("'client_id' is required in configuration")
        
        # Handle target_type - this is tricky since we need to resolve the class
        target_type_name = data.get('target_type')
        if not target_type_name:
            raise ValueError("'target_type' is required in configuration")
        
        # For now, store the type name as string - the actual type resolution
        # would need to be handled by the caller or through a registry
        target_type = target_type_name if isinstance(target_type_name, type) else str
        
        # Extract optional parameters with defaults
        auto_offset_reset = data.get('auto_offset_reset', 'latest')
        enable_auto_commit = data.get('enable_auto_commit', True)
        auto_create_topics = data.get('auto_create_topics', True)
        
        return cls(
            name=name,
            topic=topic,
            group_id=group_id,
            client_id=client_id,
            target_type=target_type,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=enable_auto_commit,
            auto_create_topics=auto_create_topics
        )
    
    @classmethod
    def from_file(
        cls, 
        config_file: Union[str, Path],
        env_prefix: str = "AUTOGEN_KAFKA_STREAMING",
        base_config: Optional[Dict[str, Any]] = None
    ) -> 'StreamingServiceConfig':
        """Load configuration from a file with optional environment variable overrides.
        
        Args:
            config_file: Path to JSON or YAML configuration file.
            env_prefix: Prefix for environment variables that can override file values.
            base_config: Base configuration dictionary to merge with.
            
        Returns:
            StreamingServiceConfig instance loaded from file and environment.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            ValueError: If the file format is invalid.
        """
        merged_config = ConfigLoader.load_config(
            config_file=config_file,
            env_prefix=env_prefix,
            base_config=base_config
        )
        
        return cls.from_dict(merged_config)
    
    @classmethod
    def from_env(
        cls,
        env_prefix: str = "AUTOGEN_KAFKA_STREAMING",
        base_config: Optional[Dict[str, Any]] = None
    ) -> 'StreamingServiceConfig':
        """Load configuration from environment variables.
        
        Args:
            env_prefix: Prefix for environment variables.
            base_config: Base configuration dictionary to merge with.
            
        Returns:
            StreamingServiceConfig instance loaded from environment variables.
            
        Example:
            Environment variables:
            AUTOGEN_KAFKA_STREAMING_NAME=my-streaming-service
            AUTOGEN_KAFKA_STREAMING_TOPIC=my-topic
            AUTOGEN_KAFKA_STREAMING_GROUP_ID=my-group
            AUTOGEN_KAFKA_STREAMING_CLIENT_ID=my-client
            AUTOGEN_KAFKA_STREAMING_TARGET_TYPE=MyEventType
        """
        merged_config = ConfigLoader.load_config(
            config_file=None,
            env_prefix=env_prefix,
            base_config=base_config
        )
        
        return cls.from_dict(merged_config)

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
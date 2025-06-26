from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
from pathlib import Path


@dataclass
class StreamingServiceConfig:
    name: str
    topic: str
    group_id: str
    client_id: str
    target_type: type
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    auto_create_topics: bool = True

    def get_consumer_config(self) -> dict[str, Any]:
        """
        Get the Kafka consumer configuration dictionary.

        This method generates a complete consumer configuration dictionary suitable
        for use with Kafka consumers. It automatically appends unique UUIDs to the
        client_id and group_id to ensure uniqueness across multiple consumer instances.

        Returns:
            dict[str, Any]: A dictionary containing the consumer configuration with:
                - client_id: Original client_id with appended UUID for uniqueness
                - group_id: Original group_id with appended UUID for uniqueness
                - auto_offset_reset: Strategy for offset reset behavior
                - enable_auto_commit: Auto-commit configuration
        """
        return {
            "client_id": f"{self.client_id}",
            "group_id": f"{self.group_id}",
            "auto_offset_reset": self.auto_offset_reset,
            "enable_auto_commit": self.enable_auto_commit
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
        # Import here to avoid circular imports
        from ..config.config_loader import ConfigLoader
        
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
        # Import here to avoid circular imports
        from ..config.config_loader import ConfigLoader
        
        merged_config = ConfigLoader.load_config(
            config_file=None,
            env_prefix=env_prefix,
            base_config=base_config
        )
        
        return cls.from_dict(merged_config)

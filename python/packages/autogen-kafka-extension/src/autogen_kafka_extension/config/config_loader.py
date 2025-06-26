"""Configuration loader utility for autogen-kafka-extension.

This module provides utilities to load configuration from various sources:
- JSON and YAML files
- Environment variables
- Dictionary objects

The loader supports configuration merging with priority order:
Environment variables > File configuration > Default values
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union, TypeVar
import logging

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from .base_config import BaseConfig

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseConfig)

class ConfigLoader:
    """Utility class for loading configuration from multiple sources."""
    
    @staticmethod
    def load_from_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from a JSON or YAML file.
        
        Args:
            file_path: Path to the configuration file.
            
        Returns:
            Dictionary containing the configuration data.
            
        Raises:
            FileNotFoundError: If the file doesn't exist.
            ValueError: If the file format is not supported or invalid.
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            if not content:
                return {}
                
            # Determine file format by extension
            if file_path.suffix.lower() in ['.yml', '.yaml']:
                if not HAS_YAML:
                    raise ValueError("YAML support not available. Install PyYAML: pip install pyyaml")
                return yaml.safe_load(content) or {}
            elif file_path.suffix.lower() == '.json':
                return json.loads(content)
            else:
                # Try to auto-detect format
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    if HAS_YAML:
                        return yaml.safe_load(content) or {}
                    else:
                        raise ValueError(f"Unsupported file format: {file_path.suffix}")
                        
        except (json.JSONDecodeError, yaml.YAMLError if HAS_YAML else Exception) as e:
            raise ValueError(f"Invalid configuration file format: {e}")
    
    @staticmethod
    def load_from_env(prefix: str = "AUTOGEN_KAFKA") -> Dict[str, Any]:
        """Load configuration from environment variables.
        
        Args:
            prefix: Prefix for environment variables (default: "AUTOGEN_KAFKA").
                   Variables should be named like PREFIX_SECTION_KEY.
                   
        Returns:
            Nested dictionary with configuration values.
            
        Example:
            Environment variables:
            AUTOGEN_KAFKA_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
            AUTOGEN_KAFKA_KAFKA_GROUP_ID=my-group
            AUTOGEN_KAFKA_SCHEMA_REGISTRY_URL=http://localhost:8081
            AUTOGEN_KAFKA_NUM_PARTITIONS=5
            
            Result:
            {
                'kafka': {
                    'bootstrap_servers': 'localhost:9092',
                    'group_id': 'my-group'
                },
                'schema_registry': {
                    'url': 'http://localhost:8081'
                },
                'num_partitions': 5
            }
        """
        config = {}
        prefix_with_separator = f"{prefix}_"
        
        for key, value in os.environ.items():
            if not key.startswith(prefix_with_separator):
                continue
                
            # Remove prefix and convert to lowercase
            config_key = key[len(prefix_with_separator):].lower()
            
            # Convert value to appropriate type
            parsed_value = ConfigLoader._parse_env_value(value)
            
            # Check if this looks like a sectioned key (has multiple underscores and first part looks like a section)
            parts = config_key.split('_')
            if len(parts) >= 2:
                # Handle special cases first
                if parts[0] == 'schema' and parts[1] == 'registry':
                    # SCHEMA_REGISTRY_* should become schema_registry.*
                    section = 'schema_registry'
                    key_name = '_'.join(parts[2:]) if len(parts) > 2 else ''
                    
                    if section not in config:
                        config[section] = {}
                    config[section][key_name] = parsed_value
                elif parts[0] in ['kafka', 'memory', 'agent', 'worker', 'streaming']:
                    # Treat as sectioned: first part is section, rest joined with underscore is key
                    section = parts[0]
                    key_name = '_'.join(parts[1:])
                    
                    if section not in config:
                        config[section] = {}
                    config[section][key_name] = parsed_value
                else:
                    # Treat as flat key (join all parts back with underscore)
                    config[config_key] = parsed_value
            else:
                # Single part, treat as flat key
                config[config_key] = parsed_value
            
        return config
    
    @staticmethod
    def _parse_env_value(value: str) -> Any:
        """Parse environment variable value to appropriate Python type.
        
        Args:
            value: String value from environment variable.
            
        Returns:
            Parsed value (str, int, float, bool, or list).
        """
        # Handle empty values
        if not value:
            return ""
        
        # Handle boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Handle numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Handle comma-separated lists
        if ',' in value:
            return [item.strip() for item in value.split(',') if item.strip()]
        
        # Return as string
        return value
    
    @staticmethod
    def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries.
        
        Later configurations override earlier ones for matching keys.
        Nested dictionaries are merged recursively.
        
        Args:
            *configs: Configuration dictionaries to merge.
            
        Returns:
            Merged configuration dictionary.
        """
        result = {}
        
        for config in configs:
            if not config:
                continue
                
            result = ConfigLoader._deep_merge(result, config)
        
        return result
    
    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries.
        
        Args:
            base: Base dictionary.
            override: Dictionary with values to override.
            
        Returns:
            Merged dictionary.
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
    
    @staticmethod
    def load_config(
        config_file: Optional[Union[str, Path]] = None,
        env_prefix: str = "AUTOGEN_KAFKA",
        base_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Load configuration from multiple sources with priority merging.
        
        Priority order (highest to lowest):
        1. Environment variables
        2. Configuration file
        3. Base configuration
        
        Args:
            config_file: Path to configuration file (JSON or YAML).
            env_prefix: Prefix for environment variables.
            base_config: Base configuration dictionary.
            
        Returns:
            Merged configuration dictionary.
            
        Raises:
            FileNotFoundError: If config_file is specified but doesn't exist.
            ValueError: If config_file has invalid format.
        """
        configs = []
        
        # Add base configuration if provided
        if base_config:
            configs.append(base_config)
            
        # Load from file if specified
        if config_file:
            try:
                file_config = ConfigLoader.load_from_file(config_file)
                configs.append(file_config)
                logger.info(f"Loaded configuration from file: {config_file}")
            except Exception as e:
                logger.error(f"Failed to load configuration file {config_file}: {e}")
                raise
        
        # Load from environment variables
        env_config = ConfigLoader.load_from_env(env_prefix)
        if env_config:
            configs.append(env_config)
            logger.info(f"Loaded configuration from environment variables with prefix: {env_prefix}")
        
        # Merge all configurations
        merged_config = ConfigLoader.merge_configs(*configs)
        
        return merged_config 
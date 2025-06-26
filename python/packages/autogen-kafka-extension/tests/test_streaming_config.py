"""Tests for streaming configuration functionality."""

import json
import os
import tempfile
from pathlib import Path
import pytest

from autogen_kafka_extension.config.streaming_config import StreamingServiceConfig as ConfigStreamingServiceConfig
from autogen_kafka_extension.shared.streaming_service_config import StreamingServiceConfig as SharedStreamingServiceConfig


class TestConfigStreamingServiceConfig:
    """Test configuration loading for config.streaming_config.StreamingServiceConfig."""
    
    def test_from_dict(self):
        """Test creating StreamingServiceConfig from dictionary."""
        config_data = {
            "name": "test-streaming-service",
            "topic": "test-topic",
            "group_id": "test-group",
            "client_id": "test-client",
            "target_type": "TestEvent",
            "auto_offset_reset": "earliest",
            "enable_auto_commit": False,
            "auto_create_topics": False
        }
        
        config = ConfigStreamingServiceConfig.from_dict(config_data)
        
        assert config.name == "test-streaming-service"
        assert config.topic == "test-topic"
        assert config.group_id == "test-group"
        assert config.client_id == "test-client"
        assert config.target_type == str  # We simplified to use str for now
        assert config.auto_offset_reset == "earliest"
        assert config.enable_auto_commit == False
        assert config.auto_create_topics == False
    
    def test_from_dict_with_defaults(self):
        """Test creating StreamingServiceConfig from dictionary with default values."""
        config_data = {
            "name": "test-streaming-service",
            "topic": "test-topic",
            "group_id": "test-group",
            "client_id": "test-client",
            "target_type": "TestEvent"
        }
        
        config = ConfigStreamingServiceConfig.from_dict(config_data)
        
        assert config.auto_offset_reset == "latest"
        assert config.enable_auto_commit == True
        assert config.auto_create_topics == True
    
    def test_from_env(self):
        """Test loading StreamingServiceConfig from environment variables."""
        env_vars = {
            "AUTOGEN_KAFKA_STREAMING_NAME": "env-streaming-service",
            "AUTOGEN_KAFKA_STREAMING_TOPIC": "env-topic",
            "AUTOGEN_KAFKA_STREAMING_GROUP_ID": "env-group",
            "AUTOGEN_KAFKA_STREAMING_CLIENT_ID": "env-client",
            "AUTOGEN_KAFKA_STREAMING_TARGET_TYPE": "EnvEvent",
            "AUTOGEN_KAFKA_STREAMING_AUTO_OFFSET_RESET": "earliest",
            "AUTOGEN_KAFKA_STREAMING_ENABLE_AUTO_COMMIT": "false",
            "AUTOGEN_KAFKA_STREAMING_AUTO_CREATE_TOPICS": "false"
        }
        
        # Store original values
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            config = ConfigStreamingServiceConfig.from_env()
            
            assert config.name == "env-streaming-service"
            assert config.topic == "env-topic"
            assert config.group_id == "env-group"
            assert config.client_id == "env-client"
            assert config.auto_offset_reset == "earliest"
            assert config.enable_auto_commit == False
            assert config.auto_create_topics == False
            
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    def test_from_file(self):
        """Test loading StreamingServiceConfig from JSON file."""
        config_data = {
            "name": "file-streaming-service",
            "topic": "file-topic",
            "group_id": "file-group",
            "client_id": "file-client",
            "target_type": "FileEvent"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            config = ConfigStreamingServiceConfig.from_file(config_file)
            
            assert config.name == "file-streaming-service"
            assert config.topic == "file-topic"
            assert config.group_id == "file-group"
            assert config.client_id == "file-client"
            
        finally:
            os.unlink(config_file)


class TestSharedStreamingServiceConfig:
    """Test configuration loading for shared.streaming_service_config.StreamingServiceConfig."""
    
    def test_from_dict(self):
        """Test creating shared StreamingServiceConfig from dictionary."""
        config_data = {
            "name": "shared-test-streaming-service",
            "topic": "shared-test-topic",
            "group_id": "shared-test-group",
            "client_id": "shared-test-client",
            "target_type": "SharedTestEvent",
            "auto_offset_reset": "earliest",
            "enable_auto_commit": False,
            "auto_create_topics": False
        }
        
        config = SharedStreamingServiceConfig.from_dict(config_data)
        
        assert config.name == "shared-test-streaming-service"
        assert config.topic == "shared-test-topic"
        assert config.group_id == "shared-test-group"
        assert config.client_id == "shared-test-client"
        assert config.target_type == str  # We simplified to use str for now
        assert config.auto_offset_reset == "earliest"
        assert config.enable_auto_commit == False
        assert config.auto_create_topics == False
    
    def test_from_env(self):
        """Test loading shared StreamingServiceConfig from environment variables."""
        env_vars = {
            "AUTOGEN_KAFKA_STREAMING_NAME": "shared-env-streaming-service",
            "AUTOGEN_KAFKA_STREAMING_TOPIC": "shared-env-topic",
            "AUTOGEN_KAFKA_STREAMING_GROUP_ID": "shared-env-group",
            "AUTOGEN_KAFKA_STREAMING_CLIENT_ID": "shared-env-client",
            "AUTOGEN_KAFKA_STREAMING_TARGET_TYPE": "SharedEnvEvent"
        }
        
        # Store original values
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            config = SharedStreamingServiceConfig.from_env()
            
            assert config.name == "shared-env-streaming-service"
            assert config.topic == "shared-env-topic"
            assert config.group_id == "shared-env-group"
            assert config.client_id == "shared-env-client"
            
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value


class TestStreamingEnvironmentVariableParsing:
    """Test that the improved environment variable parsing works for streaming configs."""
    
    def test_streaming_section_parsing(self):
        """Test that STREAMING_* environment variables are correctly parsed."""
        from autogen_kafka_extension.config.config_loader import ConfigLoader
        
        env_vars = {
            "TEST_PREFIX_STREAMING_NAME": "test-service",
            "TEST_PREFIX_STREAMING_GROUP_ID": "test-group",
            "TEST_PREFIX_STREAMING_CLIENT_ID": "test-client",
            "TEST_PREFIX_SOME_FLAT_VALUE": "flat-value"
        }
        
        # Store original values
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            result = ConfigLoader.load_from_env("TEST_PREFIX")
            
            expected = {
                "streaming": {
                    "name": "test-service",
                    "group_id": "test-group",
                    "client_id": "test-client"
                },
                "some_flat_value": "flat-value"
            }
            
            assert result == expected
            
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value 
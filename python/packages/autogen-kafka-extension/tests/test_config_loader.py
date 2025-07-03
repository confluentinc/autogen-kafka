"""Tests for configuration loading functionality."""

import json
import os
import tempfile
from pathlib import Path
import pytest

from autogen_kafka_extension.config import (
    ConfigLoader, 
    KafkaConfig, 
    KafkaAgentConfig,
    SchemaRegistryConfig
)


class TestConfigLoader:
    """Test configuration loading utilities."""
    
    def test_load_from_json_file(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "test_key": "test_value",
            "nested": {
                "inner_key": "inner_value",
                "number": 42
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            result = ConfigLoader.load_from_file(config_file)
            assert result == config_data
        finally:
            os.unlink(config_file)
    
    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        # Set test environment variables
        env_vars = {
            "TEST_PREFIX_KAFKA_BOOTSTRAP_SERVERS": "localhost:9092,localhost:9093",
            "TEST_PREFIX_KAFKA_GROUP_ID": "test-group",
            "TEST_PREFIX_SCHEMA_REGISTRY_URL": "http://localhost:8081",
            "TEST_PREFIX_NUM_PARTITIONS": "5",
            "TEST_PREFIX_IS_ENABLED": "true"
        }
        
        # Store original values
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            result = ConfigLoader.load_from_env("TEST_PREFIX")
            
            expected = {
                "kafka": {
                    "bootstrap_servers": ["localhost:9092", "localhost:9093"],
                    "group_id": "test-group"
                },
                "schema_registry": {
                    "url": "http://localhost:8081"
                },
                "num_partitions": 5,
                "is_enabled": True
            }
            
            assert result == expected
            
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    def test_merge_configs(self):
        """Test merging multiple configuration dictionaries."""
        base_config = {
            "name": "base",
            "kafka": {
                "bootstrap_servers": ["localhost:9092"],
                "group_id": "base-group"
            },
            "num_partitions": 3
        }
        
        override_config = {
            "name": "override",
            "kafka": {
                "group_id": "override-group",
                "client_id": "new-client"
            }
        }
        
        result = ConfigLoader.merge_configs(base_config, override_config)
        
        expected = {
            "name": "override",
            "kafka": {
                "bootstrap_servers": ["localhost:9092"],
                "group_id": "override-group",
                "client_id": "new-client"
            },
            "num_partitions": 3
        }
        
        assert result == expected
    
    def test_parse_env_value(self):
        """Test parsing environment variable values to appropriate types."""
        assert ConfigLoader._parse_env_value("true") == True
        assert ConfigLoader._parse_env_value("false") == False
        assert ConfigLoader._parse_env_value("42") == 42
        assert ConfigLoader._parse_env_value("3.14") == 3.14
        assert ConfigLoader._parse_env_value("hello,world,test") == ["hello", "world", "test"]
        assert ConfigLoader._parse_env_value("simple_string") == "simple_string"
        assert ConfigLoader._parse_env_value("") == ""


class TestKafkaConfigLoading:
    """Test loading KafkaConfig from various sources."""
    
    def test_kafka_config_from_dict(self):
        """Test creating KafkaConfig from dictionary."""
        config_data = {
            "name": "test-kafka",
            "group_id": "test-group",
            "client_id": "test-client",
            "bootstrap_servers": ["localhost:9092"],
            "schema_registry": {
                "url": "http://localhost:8081",
                "username": "test-user",
                "password": "test-pass"
            },
            "num_partitions": 5,
            "replication_factor": 2,
            "is_compacted": True
        }
        
        kafka_config = KafkaConfig.from_dict(config_data)
        
        assert kafka_config.name == "test-kafka"
        assert kafka_config.group_id == "test-group"
        assert kafka_config.client_id == "test-client"
        assert kafka_config.bootstrap_servers == ["localhost:9092"]
        assert kafka_config.num_partitions == 5
        assert kafka_config.replication_factor == 2
        assert kafka_config.is_compacted == True
        assert kafka_config.schema_registry_config.url == "http://localhost:8081"
        assert kafka_config.schema_registry_config.api_key == "test-user"
        assert kafka_config.schema_registry_config.api_secret == "test-pass"
    
    def test_kafka_config_from_file(self):
        """Test loading KafkaConfig from JSON file."""
        config_data = {
            "name": "file-kafka",
            "group_id": "file-group",
            "client_id": "file-client",
            "bootstrap_servers": "localhost:9092,localhost:9093",
            "schema_registry": {
                "url": "http://localhost:8081"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            kafka_config = KafkaConfig.from_file(config_file)
            
            assert kafka_config.name == "file-kafka"
            assert kafka_config.group_id == "file-group"
            assert kafka_config.bootstrap_servers == ["localhost:9092", "localhost:9093"]
            assert kafka_config.schema_registry_config.url == "http://localhost:8081"
            
        finally:
            os.unlink(config_file)
    
    def test_kafka_config_from_env(self):
        """Test loading KafkaConfig from environment variables."""
        env_vars = {
            "AUTOGEN_KAFKA_NAME": "env-kafka",
            "AUTOGEN_KAFKA_GROUP_ID": "env-group",
            "AUTOGEN_KAFKA_CLIENT_ID": "env-client",
            "AUTOGEN_KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "AUTOGEN_KAFKA_SCHEMA_REGISTRY_URL": "http://localhost:8081",
            "AUTOGEN_KAFKA_NUM_PARTITIONS": "4"
        }
        
        # Store original values
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            kafka_config = KafkaConfig.from_env()
            
            assert kafka_config.name == "env-kafka"
            assert kafka_config.group_id == "env-group"
            assert kafka_config.client_id == "env-client"
            assert kafka_config.bootstrap_servers == ["localhost:9092"]
            assert kafka_config.num_partitions == 4
            
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value


class TestSchemaRegistryConfigLoading:
    """Test loading SchemaRegistryConfig from various sources."""
    
    def test_schema_registry_config_from_dict(self):
        """Test creating SchemaRegistryConfig from dictionary."""
        config_data = {
            "url": "http://localhost:8081",
            "username": "test-user",
            "password": "test-pass"
        }
        
        config = SchemaRegistryConfig.from_dict(config_data)
        
        assert config.url == "http://localhost:8081"
        assert config.api_key == "test-user"
        assert config.api_secret == "test-pass"
    
    def test_schema_registry_config_defaults(self):
        """Test SchemaRegistryConfig with default values."""
        config_data = {}
        
        config = SchemaRegistryConfig.from_dict(config_data)
        
        assert config.url == "http://localhost:8081"
        assert config.api_key is None
        assert config.api_secret is None


class TestKafkaAgentConfigLoading:
    """Test loading KafkaAgentConfig from various sources."""
    
    def test_kafka_agent_config_from_dict(self):
        """Test creating KafkaAgentConfig from dictionary."""
        config_data = {
            "kafka": {
                "name": "agent-kafka",
                "group_id": "agent-group",
                "client_id": "agent-client",
                "bootstrap_servers": ["localhost:9092"],
                "schema_registry": {
                    "url": "http://localhost:8081"
                }
            },
            "agent" : {
                "request_topic": "custom_requests",
                "response_topic": "custom_responses"
            }
        }
        
        agent_config = KafkaAgentConfig.from_dict(config_data)
        
        assert agent_config.kafka_config.name == "agent-kafka"
        assert agent_config.request_topic == "custom_requests"
        assert agent_config.response_topic == "custom_responses"
    
    def test_kafka_agent_config_defaults(self):
        """Test KafkaAgentConfig with default topic names."""
        config_data = {
            "kafka": {
                "name": "agent-kafka",
                "group_id": "agent-group",
                "client_id": "agent-client",
                "bootstrap_servers": ["localhost:9092"],
                "schema_registry": {
                    "url": "http://localhost:8081"
                }
            }
        }
        
        agent_config = KafkaAgentConfig.from_dict(config_data)
        
        assert agent_config.request_topic == "agent_request"
        assert agent_config.response_topic == "agent_response" 
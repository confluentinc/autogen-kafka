"""Tests for KafkaMemoryConfig functionality."""

import json
import os
import tempfile
from pathlib import Path
import pytest

from autogen_kafka_extension.config import KafkaMemoryConfig, SchemaRegistryConfig
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism


class TestKafkaMemoryConfig:
    """Test KafkaMemoryConfig loading from various sources."""
    
    def test_from_dict_complete(self):
        """Test creating KafkaMemoryConfig from complete dictionary."""
        config_data = {
            "name": "test-memory-kafka",
            "group_id": "memory-group",
            "client_id": "memory-client",
            "bootstrap_servers": ["localhost:9092"],
            "schema_registry": {
                "url": "http://localhost:8081",
                "username": "test-user",
                "password": "test-pass"
            },
            "memory": {
                "memory_topic": "custom_memory_topic"
            },
            "num_partitions": 1,
            "replication_factor": 2,
            "is_compacted": False,
            "auto_offset_reset": "earliest",
            "security_protocol": "PLAINTEXT",
            "sasl_plain_username": "test-username",
            "sasl_plain_password": "test-password"
        }
        
        memory_config = KafkaMemoryConfig.from_dict(config_data)
        
        # Test basic properties
        assert memory_config.kafka_config.name == "test-memory-kafka"
        assert memory_config.kafka_config.group_id == "memory-group"
        assert memory_config.kafka_config.client_id == "memory-client"
        assert memory_config.kafka_config.bootstrap_servers == ["localhost:9092"]
        assert memory_config.kafka_config.num_partitions == 1
        assert memory_config.kafka_config.replication_factor == 2
        assert memory_config.kafka_config.is_compacted == False
        assert memory_config.kafka_config.auto_offset_reset == "earliest"
        assert memory_config.kafka_config.security_protocol == SecurityProtocol.PLAINTEXT
        assert memory_config.kafka_config.sasl_plain_username == "test-username"
        assert memory_config.kafka_config.sasl_plain_password == "test-password"
        
        # Test memory-specific properties
        assert memory_config.memory_topic == "custom_memory_topic"
        
        # Test schema registry config
        assert memory_config.kafka_config.schema_registry_config.url == "http://localhost:8081"
        assert memory_config.kafka_config.schema_registry_config.api_key == "test-user"
        assert memory_config.kafka_config.schema_registry_config.api_secret == "test-pass"
    
    def test_from_dict_with_defaults(self):
        """Test creating KafkaMemoryConfig with default values."""
        config_data = {
            "name": "test-memory-kafka",
            "group_id": "memory-group",
            "client_id": "memory-client",
            "bootstrap_servers": ["localhost:9092"],
            "schema_registry": {
                "url": "http://localhost:8081"
            }
            # No memory section - should use defaults
        }
        
        memory_config = KafkaMemoryConfig.from_dict(config_data)
        
        # Test default memory-specific values
        assert memory_config.memory_topic == "memory"
        assert memory_config.kafka_config.num_partitions == 1  # Memory should have single partition
        assert memory_config.kafka_config.replication_factor == 3
        assert memory_config.kafka_config.is_compacted == False  # Memory should not be compacted
        assert memory_config.kafka_config.auto_offset_reset == "earliest"  # Memory should start from beginning
    
    def test_from_env(self):
        """Test loading KafkaMemoryConfig from environment variables."""
        env_vars = {
            # Basic configuration
            "AUTOGEN_KAFKA_NAME": "env-memory-kafka",
            "AUTOGEN_KAFKA_GROUP_ID": "env-memory-group",
            "AUTOGEN_KAFKA_CLIENT_ID": "env-memory-client",
            "AUTOGEN_KAFKA_BOOTSTRAP_SERVERS": "localhost:9092,localhost:9093",
            "AUTOGEN_KAFKA_SCHEMA_REGISTRY_URL": "http://localhost:8081",
            "AUTOGEN_KAFKA_NUM_PARTITIONS": "1",
            "AUTOGEN_KAFKA_REPLICATION_FACTOR": "2",
            "AUTOGEN_KAFKA_IS_COMPACTED": "false",
            "AUTOGEN_KAFKA_AUTO_OFFSET_RESET": "earliest",
            
            # Memory-specific configuration
            "AUTOGEN_KAFKA_MEMORY_MEMORY_TOPIC": "env_memory_topic",
            
            # Security configuration
            "AUTOGEN_KAFKA_SECURITY_PROTOCOL": "PLAINTEXT",
            "AUTOGEN_KAFKA_SASL_PLAIN_USERNAME": "env-username",
            "AUTOGEN_KAFKA_SASL_PLAIN_PASSWORD": "env-password"
        }
        
        # Store original values
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            memory_config = KafkaMemoryConfig.from_env()
            
            # Test basic properties
            assert memory_config.kafka_config.name == "env-memory-kafka"
            assert memory_config.kafka_config.group_id == "env-memory-group"
            assert memory_config.kafka_config.client_id == "env-memory-client"
            assert memory_config.kafka_config.bootstrap_servers == ["localhost:9092", "localhost:9093"]
            assert memory_config.kafka_config.num_partitions == 1
            assert memory_config.kafka_config.replication_factor == 2
            assert memory_config.kafka_config.is_compacted == False
            assert memory_config.kafka_config.auto_offset_reset == "earliest"
            assert memory_config.kafka_config.security_protocol == SecurityProtocol.PLAINTEXT
            assert memory_config.kafka_config.sasl_plain_username == "env-username"
            assert memory_config.kafka_config.sasl_plain_password == "env-password"
            
            # Test memory-specific properties
            assert memory_config.memory_topic == "env_memory_topic"
            
            # Test schema registry
            assert memory_config.kafka_config.schema_registry_config.url == "http://localhost:8081"
            
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    def test_from_env_with_defaults(self):
        """Test loading KafkaMemoryConfig from environment variables with defaults."""
        env_vars = {
            # Only required configuration, no memory-specific settings
            "AUTOGEN_KAFKA_NAME": "env-memory-kafka-default",
            "AUTOGEN_KAFKA_GROUP_ID": "env-memory-group-default",
            "AUTOGEN_KAFKA_CLIENT_ID": "env-memory-client-default",
            "AUTOGEN_KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "AUTOGEN_KAFKA_SCHEMA_REGISTRY_URL": "http://localhost:8081"
        }
        
        # Store original values
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            memory_config = KafkaMemoryConfig.from_env()
            
            # Test basic properties
            assert memory_config.kafka_config.name == "env-memory-kafka-default"
            assert memory_config.kafka_config.group_id == "env-memory-group-default"
            assert memory_config.kafka_config.client_id == "env-memory-client-default"
            
            # Test default memory values
            assert memory_config.memory_topic == "memory"
            assert memory_config.kafka_config.num_partitions == 1  # Memory default
            assert memory_config.kafka_config.replication_factor == 3
            assert memory_config.kafka_config.is_compacted == False  # Memory default
            assert memory_config.kafka_config.auto_offset_reset == "earliest"  # Memory default
            
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    def test_from_file(self):
        """Test loading KafkaMemoryConfig from JSON file."""
        config_data = {
            "name": "file-memory-kafka",
            "group_id": "file-memory-group",
            "client_id": "file-memory-client",
            "bootstrap_servers": "localhost:9092,localhost:9093",
            "schema_registry": {
                "url": "http://localhost:8081"
            },
            "memory": {
                "memory_topic": "file_memory_topic"
            },
            "num_partitions": 1,
            "auto_offset_reset": "earliest"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            memory_config = KafkaMemoryConfig.from_file(config_file)
            
            # Test basic properties
            assert memory_config.kafka_config.name == "file-memory-kafka"
            assert memory_config.kafka_config.group_id == "file-memory-group"
            assert memory_config.kafka_config.bootstrap_servers == ["localhost:9092", "localhost:9093"]
            
            # Test memory-specific properties
            assert memory_config.memory_topic == "file_memory_topic"
            assert memory_config.kafka_config.num_partitions == 1
            assert memory_config.kafka_config.auto_offset_reset == "earliest"
            
        finally:
            os.unlink(config_file)
    
    def test_memory_specific_defaults(self):
        """Test that memory config has appropriate defaults for memory use case."""
        config_data = {
            "name": "memory-test",
            "group_id": "memory-group",
            "client_id": "memory-client",
            "bootstrap_servers": ["localhost:9092"],
            "schema_registry": {
                "url": "http://localhost:8081"
            }
        }
        
        memory_config = KafkaMemoryConfig.from_dict(config_data)
        
        # Memory should have single partition for ordered processing
        assert memory_config.kafka_config.num_partitions == 1
        
        # Memory should not be compacted to preserve all memory events
        assert memory_config.kafka_config.is_compacted == False
        
        # Memory should start from earliest to rebuild full history
        assert memory_config.kafka_config.auto_offset_reset == "earliest"
        
        # Default memory topic
        assert memory_config.memory_topic == "memory"
    
    def test_validation_errors(self):
        """Test that validation catches missing required fields."""
        # Missing name
        with pytest.raises(ValueError, match="'name' is required"):
            KafkaMemoryConfig.from_dict({
                "group_id": "test-group",
                "client_id": "test-client",
                "bootstrap_servers": ["localhost:9092"],
                "schema_registry": {"url": "http://localhost:8081"}
            })
        
        # Missing group_id
        with pytest.raises(ValueError, match="'group_id' is required"):
            KafkaMemoryConfig.from_dict({
                "name": "test-name",
                "client_id": "test-client",
                "bootstrap_servers": ["localhost:9092"],
                "schema_registry": {"url": "http://localhost:8081"}
            })
        
        # Missing schema_registry.url
        with pytest.raises(ValueError, match="'schema_registry.url' is required"):
            KafkaMemoryConfig.from_dict({
                "name": "test-name",
                "group_id": "test-group",
                "client_id": "test-client",
                "bootstrap_servers": ["localhost:9092"],
                "schema_registry": {}
            })


class TestKafkaMemoryConfigEnvironmentVariableParsing:
    """Test that the improved environment variable parsing works for memory configs."""
    
    def test_memory_section_parsing(self):
        """Test that MEMORY_* environment variables are correctly parsed."""
        from autogen_kafka_extension.config.config_loader import ConfigLoader
        
        env_vars = {
            "TEST_PREFIX_NAME": "test-memory",
            "TEST_PREFIX_GROUP_ID": "test-group",
            "TEST_PREFIX_MEMORY_MEMORY_TOPIC": "test-memory-topic",
            "TEST_PREFIX_SCHEMA_REGISTRY_URL": "http://localhost:8081",
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
                "name": "test-memory",
                "group_id": "test-group",
                "memory": {
                    "memory_topic": "test-memory-topic"
                },
                "schema_registry": {
                    "url": "http://localhost:8081"
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
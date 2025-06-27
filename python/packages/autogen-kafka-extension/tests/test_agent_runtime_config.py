"""Tests for KafkaWorkerConfig functionality."""

import json
import os
import tempfile
from pathlib import Path
import pytest

from autogen_kafka_extension.config import KafkaAgentRuntimeConfig, KafkaConfig, SchemaRegistryConfig


class TestKafkaWorkerConfig:
    """Test KafkaWorkerConfig loading from various sources."""
    
    def test_from_dict_complete(self):
        """Test creating KafkaWorkerConfig from complete dictionary."""
        config_data = {
            "kafka": {
                "name": "test-worker-kafka",
                "group_id": "worker-group",
                "client_id": "worker-client",
                "bootstrap_servers": ["localhost:9092"],
                "schema_registry": {
                    "url": "http://localhost:8081",
                    "username": "test-user",
                    "password": "test-pass"
                },
                "num_partitions": 5,
                "replication_factor": 2,
                "is_compacted": True
            },
            "runtime": {
                "request_topic": "custom_worker_requests",
                "response_topic": "custom_worker_responses",
                "registry_topic": "custom_agent_registry",
                "subscription_topic": "custom_agent_subscriptions",
                "publish_topic": "custom_agent_publishes"
            }
        }
        
        worker_config = KafkaAgentRuntimeConfig.from_dict(config_data)
        
        # Test kafka config properties
        assert worker_config.kafka_config.name == "test-worker-kafka"
        assert worker_config.kafka_config.group_id == "worker-group"
        assert worker_config.kafka_config.client_id == "worker-client"
        assert worker_config.kafka_config.bootstrap_servers == ["localhost:9092"]
        assert worker_config.kafka_config.num_partitions == 5
        assert worker_config.kafka_config.replication_factor == 2
        assert worker_config.kafka_config.is_compacted == True
        
        # Test worker-specific properties
        assert worker_config.request_topic == "custom_worker_requests"
        assert worker_config.response_topic == "custom_worker_responses"
        assert worker_config.registry_topic == "custom_agent_registry"
        assert worker_config.subscription_topic == "custom_agent_subscriptions"
        assert worker_config.publish_topic == "custom_agent_publishes"
    
    def test_from_dict_with_defaults(self):
        """Test creating KafkaWorkerConfig with default worker topic names."""
        config_data = {
            "kafka": {
                "name": "test-worker-kafka",
                "group_id": "worker-group",
                "client_id": "worker-client",
                "bootstrap_servers": ["localhost:9092"],
                "schema_registry": {
                    "url": "http://localhost:8081"
                }
            }
            # No worker section - should use defaults
        }
        
        worker_config = KafkaAgentRuntimeConfig.from_dict(config_data)
        
        # Test default worker topic names
        assert worker_config.request_topic == "worker_requests"
        assert worker_config.response_topic == "worker_responses"
        assert worker_config.registry_topic == "agent_registry"
        assert worker_config.subscription_topic == "agent_subscriptions"
        assert worker_config.publish_topic == "agent_publishes"
    
    def test_from_env(self):
        """Test loading KafkaWorkerConfig from environment variables."""
        env_vars = {
            # Kafka configuration
            "AUTOGEN_KAFKA_KAFKA_NAME": "env-worker-kafka",
            "AUTOGEN_KAFKA_KAFKA_GROUP_ID": "env-worker-group",
            "AUTOGEN_KAFKA_KAFKA_CLIENT_ID": "env-worker-client",
            "AUTOGEN_KAFKA_KAFKA_BOOTSTRAP_SERVERS": "localhost:9092,localhost:9093",
            "AUTOGEN_KAFKA_SCHEMA_REGISTRY_URL": "http://localhost:8081",
            "AUTOGEN_KAFKA_KAFKA_NUM_PARTITIONS": "4",
            
            # Worker-specific configuration
            "AUTOGEN_KAFKA_RUNTIME_REQUEST_TOPIC": "env_worker_requests",
            "AUTOGEN_KAFKA_RUNTIME_RESPONSE_TOPIC": "env_worker_responses",
            "AUTOGEN_KAFKA_RUNTIME_REGISTRY_TOPIC": "env_agent_registry",
            "AUTOGEN_KAFKA_RUNTIME_SUBSCRIPTION_TOPIC": "env_agent_subscriptions",
            "AUTOGEN_KAFKA_RUNTIME_PUBLISH_TOPIC": "env_agent_publishes"
        }
        
        # Store original values
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            worker_config = KafkaAgentRuntimeConfig.from_env()
            
            # Test kafka config properties
            assert worker_config.kafka_config.name == "env-worker-kafka"
            assert worker_config.kafka_config.group_id == "env-worker-group"
            assert worker_config.kafka_config.client_id == "env-worker-client"
            assert worker_config.kafka_config.bootstrap_servers == ["localhost:9092", "localhost:9093"]
            assert worker_config.kafka_config.num_partitions == 4
            
            # Test worker-specific properties
            assert worker_config.request_topic == "env_worker_requests"
            assert worker_config.response_topic == "env_worker_responses"
            assert worker_config.registry_topic == "env_agent_registry"
            assert worker_config.subscription_topic == "env_agent_subscriptions"
            assert worker_config.publish_topic == "env_agent_publishes"
            
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    def test_from_env_with_defaults(self):
        """Test loading KafkaWorkerConfig from environment variables with default worker topics."""
        env_vars = {
            # Only Kafka configuration, no worker-specific settings
            "AUTOGEN_KAFKA_KAFKA_NAME": "env-worker-kafka-default",
            "AUTOGEN_KAFKA_KAFKA_GROUP_ID": "env-worker-group-default",
            "AUTOGEN_KAFKA_KAFKA_CLIENT_ID": "env-worker-client-default",
            "AUTOGEN_KAFKA_KAFKA_BOOTSTRAP_SERVERS": "localhost:9092",
            "AUTOGEN_KAFKA_SCHEMA_REGISTRY_URL": "http://localhost:8081"
        }
        
        # Store original values
        original_env = {}
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            worker_config = KafkaAgentRuntimeConfig.from_env()
            
            # Test kafka config properties
            assert worker_config.kafka_config.name == "env-worker-kafka-default"
            assert worker_config.kafka_config.group_id == "env-worker-group-default"
            assert worker_config.kafka_config.client_id == "env-worker-client-default"
            
            # Test default worker topics (should use class defaults)
            assert worker_config.request_topic == "worker_requests"
            assert worker_config.response_topic == "worker_responses"
            assert worker_config.registry_topic == "agent_registry"
            assert worker_config.subscription_topic == "agent_subscriptions"
            assert worker_config.publish_topic == "agent_publishes"
            
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    def test_from_file(self):
        """Test loading KafkaWorkerConfig from JSON file."""
        config_data = {
            "kafka": {
                "name": "file-worker-kafka",
                "group_id": "file-worker-group",
                "client_id": "file-worker-client",
                "bootstrap_servers": "localhost:9092,localhost:9093",
                "schema_registry": {
                    "url": "http://localhost:8081"
                }
            },
            "runtime": {
                "request_topic": "file_worker_requests",
                "response_topic": "file_worker_responses",
                "registry_topic": "file_agent_registry"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            worker_config = KafkaAgentRuntimeConfig.from_file(config_file)
            
            # Test kafka config properties
            assert worker_config.kafka_config.name == "file-worker-kafka"
            assert worker_config.kafka_config.group_id == "file-worker-group"
            assert worker_config.kafka_config.bootstrap_servers == ["localhost:9092", "localhost:9093"]
            
            # Test worker-specific properties
            assert worker_config.request_topic == "file_worker_requests"
            assert worker_config.response_topic == "file_worker_responses"
            assert worker_config.registry_topic == "file_agent_registry"
            
            # Test defaults for unspecified topics
            assert worker_config.subscription_topic == "agent_subscriptions"
            assert worker_config.publish_topic == "agent_publishes"
            
        finally:
            os.unlink(config_file)
    
    def test_get_all_topics(self):
        """Test that get_all_topics returns all configured topics."""
        config_data = {
            "kafka": {
                "name": "test-kafka",
                "group_id": "test-group",
                "client_id": "test-client",
                "bootstrap_servers": ["localhost:9092"],
                "schema_registry": {
                    "url": "http://localhost:8081"
                }
            },
            "runtime": {
                "request_topic": "test_requests",
                "response_topic": "test_responses",
                "registry_topic": "test_registry",
                "subscription_topic": "test_subscriptions",
                "publish_topic": "test_publishes"
            }
        }
        
        worker_config = KafkaAgentRuntimeConfig.from_dict(config_data)
        all_topics = worker_config.get_all_topics()
        
        expected_topics = [
            "test_requests",
            "test_responses", 
            "test_registry",
            "test_subscriptions",
            "test_publishes"
        ]
        
        assert all_topics == expected_topics
        assert len(set(all_topics)) == len(all_topics)  # All topics should be unique


class TestKafkaWorkerConfigEnvironmentVariableParsing:
    """Test that the improved environment variable parsing works for worker configs."""
    
    def test_worker_section_parsing(self):
        """Test that WORKER_* environment variables are correctly parsed."""
        from autogen_kafka_extension.config.config_loader import ConfigLoader
        
        env_vars = {
            "TEST_PREFIX_KAFKA_GROUP_ID": "test-group",
            "TEST_PREFIX_WORKER_REQUEST_TOPIC": "test-requests",
            "TEST_PREFIX_WORKER_RESPONSE_TOPIC": "test-responses",
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
                "kafka": {
                    "group_id": "test-group"
                },
                "runtime": {
                    "request_topic": "test-requests",
                    "response_topic": "test-responses"
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
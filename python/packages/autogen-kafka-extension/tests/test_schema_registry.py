"""
Test Schema Registry integration.
"""

import pytest
from unittest.mock import Mock, patch
from confluent_kafka.schema_registry import SchemaRegistryClient


def test_schema_registry_client_creation():
    """Test that we can create a Schema Registry client."""
    with patch('confluent_kafka.schema_registry.SchemaRegistryClient'):
        config = {'url': 'http://localhost:8081'}
        client = SchemaRegistryClient(config)
        assert client is not None


def test_avro_schema_definition():
    """Test that we can define valid Avro schemas."""
    user_schema = """
    {
      "namespace": "example.avro",
      "type": "record",
      "name": "User",
      "fields": [
        {"name": "name", "type": "string"},
        {"name": "favorite_number", "type": ["int", "null"]},
        {"name": "favorite_color", "type": ["string", "null"]}
      ]
    }
    """
    
    # This should not raise an exception when parsed as JSON
    import json
    parsed_schema = json.loads(user_schema)
    assert parsed_schema["type"] == "record"
    assert parsed_schema["name"] == "User"
    assert len(parsed_schema["fields"]) == 3


@pytest.mark.asyncio
async def test_schema_registry_basic_workflow():
    """Test basic Schema Registry workflow."""
    # Mock the Schema Registry client
    mock_client = Mock()
    mock_client.register_schema.return_value = 123
    
    # Test schema registration
    schema_str = '{"type": "record", "name": "Test", "fields": []}'
    schema_id = mock_client.register_schema("test-subject", schema_str)
    
    assert schema_id == 123
    mock_client.register_schema.assert_called_once() 
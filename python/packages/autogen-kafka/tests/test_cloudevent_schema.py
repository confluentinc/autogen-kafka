"""
Tests for CloudEvent schema and serialization utilities.
"""

import json
import pytest
from datetime import datetime, timezone
from azure.core.messaging import CloudEvent
from autogen_kafka.shared.events.cloudevent_schema import (
    get_cloudevent_json_schema,
    get_cloudevent_json_schema_str,
    get_cloudevent_json_schema_compact,
    cloud_event_to_dict
)


def test_get_cloudevent_json_schema():
    """Test that get_cloudevent_json_schema returns a valid schema dictionary."""
    schema = get_cloudevent_json_schema()
    
    # Check basic structure
    assert isinstance(schema, dict)
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "required" in schema
    
    # Check required fields
    required_fields = schema["required"]
    assert "specversion" in required_fields
    assert "type" in required_fields
    assert "source" in required_fields
    assert "id" in required_fields
    
    # Check properties
    properties = schema["properties"]
    assert "specversion" in properties
    assert "type" in properties
    assert "source" in properties
    assert "id" in properties
    assert "time" in properties
    assert "data" in properties
    assert "datacontenttype" in properties
    assert "dataschema" in properties
    assert "subject" in properties


def test_get_cloudevent_json_schema_str():
    """Test that get_cloudevent_json_schema_str returns a valid formatted JSON string."""
    schema_str = get_cloudevent_json_schema_str()
    
    # Should be valid JSON
    parsed = json.loads(schema_str)
    assert isinstance(parsed, dict)
    
    # Should be formatted (contains newlines and spaces)
    assert "\n" in schema_str
    assert "  " in schema_str  # Indentation spaces
    
    # Should contain the expected schema structure
    assert parsed["type"] == "object"
    assert "properties" in parsed
    assert "required" in parsed


def test_get_cloudevent_json_schema_compact():
    """Test that get_cloudevent_json_schema_compact returns a valid compact JSON string."""
    schema_str = get_cloudevent_json_schema_compact()
    
    # Should be valid JSON
    parsed = json.loads(schema_str)
    assert isinstance(parsed, dict)
    
    # Should be compact (no extra whitespace)
    assert "\n" not in schema_str
    assert "  " not in schema_str  # No indentation
    
    # Should contain the expected schema structure
    assert parsed["type"] == "object"
    assert "properties" in parsed
    assert "required" in parsed


def test_cloud_event_to_dict():
    """Test cloud_event_to_dict function with various CloudEvent configurations."""
    # Test basic CloudEvent
    event = CloudEvent(
        source="test/source",
        type="test.event",
        id="test-123"
    )
    
    result = cloud_event_to_dict(event)
    
    assert isinstance(result, dict)
    assert result["source"] == "test/source"
    assert result["type"] == "test.event"
    assert result["id"] == "test-123"
    assert result["specversion"] == "1.0"
    
    # Test CloudEvent with all optional fields
    test_time = datetime.now(timezone.utc)
    event_full = CloudEvent(
        source="test/source",
        type="test.event",
        id="test-456",
        time=test_time,
        datacontenttype="application/json",
        dataschema="https://example.com/schema",
        subject="test-subject",
        data={"key": "value"},
        extensions={"ext1": "value1", "ext2": "value2"}
    )
    
    result_full = cloud_event_to_dict(event_full)
    
    assert result_full["time"] == test_time.isoformat()
    assert result_full["datacontenttype"] == "application/json"
    assert result_full["dataschema"] == "https://example.com/schema"
    assert result_full["subject"] == "test-subject"
    assert result_full["data"] == {"key": "value"}
    assert result_full["ext1"] == "value1"
    assert result_full["ext2"] == "value2"

def test_cloud_event_roundtrip():
    """Test that CloudEvent can be converted to dict and back."""
    original_event = CloudEvent(
        source="test/roundtrip",
        type="test.roundtrip",
        id="roundtrip-123",
        time=datetime.now(timezone.utc),
        data={"test": "data"},
        extensions={"custom": "attribute"}
    )
    
    # Convert to dict
    event_dict = cloud_event_to_dict(original_event)
    
    # Convert back to CloudEvent
    reconstructed_event = CloudEvent.from_dict(event_dict)
    
    # Verify they match
    assert reconstructed_event.source == original_event.source
    assert reconstructed_event.type == original_event.type
    assert reconstructed_event.id == original_event.id
    assert reconstructed_event.data == original_event.data
    assert reconstructed_event.extensions == original_event.extensions
    
    # Time comparison (allowing for microsecond differences)
    if original_event.time and reconstructed_event.time:
        time_diff = abs((original_event.time - reconstructed_event.time).total_seconds())
        assert time_diff < 1  # Less than 1 second difference


def test_schema_validation():
    """Test that the schema can validate CloudEvent dictionaries."""
    import jsonschema
    
    schema = get_cloudevent_json_schema()
    
    # Valid CloudEvent
    valid_event = {
        "specversion": "1.0",
        "type": "com.example.sampletype1",
        "source": "https://example.com/source",
        "id": "1234"
    }
    
    # Should not raise an exception
    jsonschema.validate(valid_event, schema)
    
    # Invalid CloudEvent (missing required field)
    invalid_event = {
        "specversion": "1.0",
        "type": "com.example.sampletype1",
        # Missing source and id
    }
    
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid_event, schema) 
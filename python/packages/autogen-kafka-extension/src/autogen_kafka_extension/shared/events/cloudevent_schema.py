"""
CloudEvent JSON Schema definitions and utilities.

This module provides JSON schema definitions for CloudEvent objects
following the CloudEvents specification v1.0.
"""

import json
import base64
from typing import Dict, Any, Optional, Union
from datetime import datetime
from azure.core.messaging import CloudEvent


def get_cloudevent_json_schema() -> Dict[str, Any]:
    """
    Returns the CloudEvent JSON schema as a dictionary.
    
    Based on the CloudEvents specification v1.0:
    https://github.com/cloudevents/spec/blob/v1.0/spec.md
    
    Returns:
        Dict[str, Any]: The CloudEvent JSON schema
    """
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "CloudEvent",
        "description": "CloudEvent v1.0 JSON Schema",
        "type": "object",
        "properties": {
            "specversion": {
                "type": "string",
                "description": "The version of the CloudEvent spec",
                "default": "1.0"
            },
            "type": {
                "type": "string",
                "description": "Type of event related to the originating occurrence",
                "minLength": 1
            },
            "source": {
                "type": "string",
                "description": "Identifies the context in which an event happened",
                "minLength": 1
            },
            "id": {
                "type": "string",
                "description": "An identifier for the event",
                "minLength": 1
            },
            "time": {
                "type": "string",
                "format": "date-time",
                "description": "The time (in UTC) the event was generated"
            },
            "datacontenttype": {
                "type": "string",
                "description": "Content type of data value"
            },
            "dataschema": {
                "type": "string",
                "format": "uri",
                "description": "Identifies the schema that data adheres to"
            },
            "subject": {
                "type": "string",
                "description": "This describes the subject of the event in the context of the event producer"
            },
            "data": {
                "description": "Event data specific to the event type"
            },
            "data_base64": {
                "type": "string",
                "description": "Base64 encoded event data (used when data is binary)"
            }
        },
        "required": ["specversion", "type", "source", "id"],
        "additionalProperties": {
            "type": ["string", "number", "integer", "boolean", "null"],
            "description": "CloudEvent extension attributes"
        },
        "not": {
            "allOf": [
                {"required": ["data"]},
                {"required": ["data_base64"]}
            ]
        }
    }


def get_cloudevent_json_schema_str() -> str:
    """
    Returns the CloudEvent JSON schema as a formatted JSON string.
    
    Returns:
        str: The CloudEvent JSON schema as a formatted JSON string
    """
    return json.dumps(get_cloudevent_json_schema(), indent=2)


def get_cloudevent_json_schema_compact() -> str:
    """
    Returns the CloudEvent JSON schema as a compact JSON string.
    
    Returns:
        str: The CloudEvent JSON schema as a compact JSON string
    """
    return json.dumps(get_cloudevent_json_schema(), separators=(',', ':'))


def _is_json_serializable(data: Any) -> bool:
    """
    Check if data can be JSON serialized.
    
    Args:
        data: The data to check
        
    Returns:
        bool: True if the data is JSON serializable, False otherwise
    """
    try:
        json.dumps(data)
        return True
    except (TypeError, ValueError):
        return False


def cloud_event_to_dict(cloud_event: CloudEvent) -> Dict[str, Any]:
    """
    Convert a CloudEvent object to a dictionary representation.
    
    This function properly handles binary data by converting it to base64 encoding
    when the data is not JSON serializable (e.g., bytes).
    
    Args:
        cloud_event: The CloudEvent object to convert
        
    Returns:
        Dict[str, Any]: Dictionary representation of the CloudEvent
    """
    result = {
        "specversion": cloud_event.specversion,
        "type": cloud_event.type,
        "source": cloud_event.source,
        "id": cloud_event.id
    }
    
    # Add optional fields if they exist and are not None
    if cloud_event.time is not None:
        if isinstance(cloud_event.time, datetime):
            result["time"] = cloud_event.time.isoformat()
        else:
            result["time"] = cloud_event.time
    
    if cloud_event.datacontenttype is not None:
        result["datacontenttype"] = cloud_event.datacontenttype
    
    if cloud_event.dataschema is not None:
        result["dataschema"] = cloud_event.dataschema
    
    if cloud_event.subject is not None:
        result["subject"] = cloud_event.subject
    
    # Handle data field - convert bytes to base64 if necessary
    if cloud_event.data is not None:
        if isinstance(cloud_event.data, (bytes, bytearray)):
            # Binary data - encode as base64
            result["data_base64"] = base64.b64encode(cloud_event.data).decode('utf-8')
        elif not _is_json_serializable(cloud_event.data):
            # Data is not JSON serializable, try to convert to base64
            try:
                # If it's a string, encode to bytes first
                if isinstance(cloud_event.data, str):
                    data_bytes = cloud_event.data.encode('utf-8')
                else:
                    # Try to convert to bytes
                    data_bytes = bytes(cloud_event.data)
                result["data_base64"] = base64.b64encode(data_bytes).decode('utf-8')
            except (TypeError, ValueError):
                # If we can't convert to bytes, try to serialize as string
                result["data"] = str(cloud_event.data)
        else:
            # Data is JSON serializable
            result["data"] = cloud_event.data
    
    # Add extension attributes if they exist
    if cloud_event.extensions:
        for key, value in cloud_event.extensions.items():
            # Ensure extension values are JSON serializable
            if isinstance(value, (bytes, bytearray)):
                result[key] = base64.b64encode(value).decode('utf-8')
            elif _is_json_serializable(value):
                result[key] = value
            else:
                result[key] = str(value)
    
    return result

def cloud_event_from_dict(data: Dict[str, Any]) -> CloudEvent:
    """
    Create a CloudEvent from a dictionary, handling base64 encoded data.
    
    This is a helper function that extends CloudEvent.from_dict() to properly
    handle data_base64 fields by converting them back to bytes.
    
    Args:
        data: Dictionary representation of CloudEvent
        
    Returns:
        CloudEvent: The reconstructed CloudEvent object
    """
    # Make a copy to avoid modifying the original
    event_data = data.copy()
    
    # Handle data_base64 field
    if "data_base64" in event_data:
        try:
            # Decode base64 data back to bytes
            decoded_data = base64.b64decode(event_data["data_base64"])
            event_data["data"] = decoded_data
            del event_data["data_base64"]
        except Exception:
            # If decoding fails, keep as string
            pass
    
    return CloudEvent.from_dict(event_data) 
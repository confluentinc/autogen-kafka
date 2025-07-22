import json
from typing import Dict, Any, cast

from pydantic import BaseModel

from ..kafka_message_type import KafkaMessageType
from ...shared.events.event_base import EventBase
from ...shared.schema_utils import SchemaUtils


class AgentEvent(EventBase):
    """
    Base class for agent events.
    This class can be extended to create specific agent events.
    """

    def __init__(self, id: str,
                 message_type: str,
                 message: Dict[str, Any]) -> None:
        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary")
        if not isinstance(message_type, str):
            raise ValueError("Message type must be a string")
        if not isinstance(id, str):
            raise ValueError("ID must be a string")

        self._id = id
        self._message = message
        self._message_type = message_type

    @property
    def id(self) -> str:
        return self._id

    @property
    def message_type(self) -> str:
        """
        The type of the message associated with the event.
        This can be used to determine how to process the message.
        """
        return self._message_type

    @property
    def message(self) -> Dict[str, Any]:
        """
        The message associated with the event.
        This is typically a serialized representation of the event data.
        """
        return self._message

    def __dict__(self) -> Dict[str, str]:
        """
        Convert the event to a dictionary representation.
        This can be useful for serialization or logging.
        """
        return {
            "id": self._id,
            "message_type": self._message_type,
            "message":  self._message
        }

    @staticmethod
    def wrap_schema(obj_type: type[KafkaMessageType | BaseModel]) -> str:
        """
        Wraps the schema of the given object type into an AgentEvent schema.
        :param obj_type: The type of the object to wrap.
        :return: A JSON string representing the AgentEvent schema with the specified message type.
        """
        message_schema = SchemaUtils.get_schema(obj_type)

        agent_schema : Dict[str, Any] = json.loads(AgentEvent.__schema__())
        cast(Dict[str, Any], agent_schema["properties"])["message"] = message_schema

        return json.dumps(agent_schema)


    @classmethod
    def __from_dict__(cls, data: Dict[str, Any]) -> 'AgentEvent':
        """
        Create an AgentEvent instance from a dictionary representation.
        This is useful for deserialization.
        """
        # Ensure that id, message_type, and message are present
        if not all(key in data for key in ["id", "message_type", "message"]):
            raise ValueError("Missing required fields in data")

        # Decode the message from base64
        return cls(id=data["id"],
                   message=data["message"],
                   message_type=data["message_type"])  # Convert back to bytes

    @classmethod
    def __schema__(cls) -> str:
        return """
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "id": {
                    "type": "string"
                },
                "message_type": {
                    "type": "string"
                },
                "message": {
                    "type": "object",
                      "additionalProperties": {
                        "type": "string"
                      }
                }
            },
            "required": ["id", "message_type", "message"]
        }
        """

    def __repr__(self):
        return f"AgentEvent(id={self._id}, message_type={self._message_type}, message_length={len(self._message)})"
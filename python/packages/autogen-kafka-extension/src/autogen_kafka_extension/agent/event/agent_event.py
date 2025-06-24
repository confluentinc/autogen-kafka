import base64
from typing import Dict

from autogen_kafka_extension.shared.events.event_base import EventBase


class AgentEvent(EventBase):
    """
    Base class for agent events.
    This class can be extended to create specific agent events.
    """

    def __init__(self, id: str,
                 message_type: str,
                 message: bytes) -> None:
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
    def message(self) -> bytes:
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
        # Base64 encode the message if needed, or keep it as bytes
        encoded = base64.b64encode(self._message).decode("ascii")

        return {
            "id": self._id,
            "message_type": self._message_type,
            "message":  encoded
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'AgentEvent':
        """
        Create an AgentEvent instance from a dictionary representation.
        This is useful for deserialization.
        """
        # Ensure that id, message_type, and message are present
        if not all(key in data for key in ["id", "message_type", "message"]):
            raise ValueError("Missing required fields in data")

        # Decode the message from base64
        try:
            message = base64.b64decode(data["message"])
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid base64 encoding for message: {e}")

        return cls(id=data["id"],
                   message=message,
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
                    "type": "string",
                    "contentEncoding": "base64"
                }
            },
            "required": ["id", "message_type", "message"]
        }
        """

    def __repr__(self):
        return f"AgentEvent(id={self._id}, message_type={self._message_type}, message_length={len(self._message)})"
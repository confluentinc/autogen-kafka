import base64
from typing import Any

from autogen_core import AgentId, TopicId

class RequestEvent(object):

    @property
    def agent_id(self) -> AgentId | None:
        return self._agent_id

    @property
    def recipient(self) -> AgentId | None:
        return self._recipient

    @property
    def topic_id(self) -> TopicId | None:
        return self._topic_id

    @property
    def message_id(self) -> str | None:
        return self._message_id

    @property
    def request_id(self) -> str | None:
        return self._request_id

    @property
    def payload(self) -> bytes | None:
        return self._payload

    @property
    def payload_type(self) -> str | None:
        return self._payload_type

    @property
    def payload_format(self) -> str | None:
        return self._payload_format

    @property
    def metadata(self) -> dict:
        return self._metadata

    @property
    def error(self) -> str:
        return self._error

    def __init__(self,
                 message_id: str | None = None,
                 agent_id: AgentId | None = None,
                 topic_id: TopicId | None = None,
                 recipient: AgentId | None = None,
                 payload: bytes | None = None,
                 payload_type: str | None = None,
                 payload_format: str | None = None,
                 request_id: str | None = None,
                 metadata: dict[str, Any] | None = None,
                 error: str | None = None,
                 values: dict[str, Any] | None = None):
        self._agent_id : AgentId | None = agent_id
        self._message_id: str | None = message_id
        self._request_id: str | None = request_id
        self._payload: bytes | None = payload
        self._payload_type: str | None = payload_type
        self._payload_format: str | None = payload_format
        self._topic_id: TopicId | None = topic_id
        self._recipient: AgentId | None = recipient
        self._metadata: dict[str, Any] | None = metadata
        self._error: str | None = error


    def to_dict(self) -> dict[str, Any]:
        """Convert the Message object to a dictionary."""
        return {
            "message_id": self._message_id,
            "topic_id": self._topic_id.__str__() if self._topic_id else None,
            "agent_id": self._agent_id.__str__() if self._agent_id else None,
            "request_id": self._request_id,
            "recipient": self._recipient.__str__() if self._recipient else None,
            "payload": base64.b64encode(self._payload).decode("ascii") if self._payload else None,
            "payload_type": self._payload_type,
            "payload_format": self._payload_format,
            "metadata": self._metadata if self._metadata else {},
            "error": self._error,
        }

    @classmethod
    def from_dict(cls, message_dict: dict[str, Any]) -> 'RequestEvent':
        # Parse enums and objects from their string representations
        message_id = message_dict.get("message_id")
        agent_id = AgentId.from_str(message_dict["agent_id"]) if message_dict.get("agent_id") else None
        topic_id = TopicId.from_str(message_dict["topic_id"]) if message_dict.get("topic_id") else None
        recipient = AgentId.from_str(message_dict["recipient"]) if message_dict.get("recipient") else None
        request_id = message_dict.get("request_id")
        payload = message_dict.get("payload")
        payload_type = message_dict.get("payload_type")
        payload_format = message_dict.get("payload_format")
        metadata = message_dict.get("metadata", {})
        error = message_dict.get("error")

        return cls(
            message_id=message_id,
            agent_id=agent_id,
            topic_id=topic_id,
            recipient=recipient,
            payload=base64.b64decode(payload) if payload else None,
            payload_type=payload_type,
            payload_format=payload_format,
            request_id=request_id,
            metadata=metadata,
            error=error
        )
from enum import Enum
from typing import Dict

from autogen_core import AgentType

from autogen_kafka.shared.events.event_base import EventBase


class RegistrationMessageType(Enum):
    REGISTER = "register"
    UNREGISTER = "unregister"

class RegistrationEvent(EventBase):

    @property
    def message_type(self) -> RegistrationMessageType:
        return self._message_type

    @property
    def agent(self) -> str:
        return self._agent

    def __init__(self, message_type: RegistrationMessageType, agent: str | AgentType):
        self._message_type = message_type
        self._agent = agent.type if isinstance(agent, AgentType) else agent

    def __dict__(self) -> Dict[str, str]:
        return {
            "message_type": self._message_type.value,
            "agent": self._agent,
        }

    @classmethod
    def __from_dict__(cls, data: Dict[str, str]) -> 'RegistrationEvent':
        return cls(
            message_type=RegistrationMessageType(data["message_type"]),
            agent= data["agent"]
        )

    @classmethod
    def __schema__(cls) -> str:
        return """
        {
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "enum": ["register", "unregister"]
                },
                "agent": {
                    "type": "string"
                }
            },
            "required": ["message_type", "agent"]
        }
        """

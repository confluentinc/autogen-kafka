from enum import Enum
from typing import Dict

from autogen_core import AgentId, AgentType


class RegistrationMessageType(Enum):
    REGISTER = "register"
    UNREGISTER = "unregister"

class RegistrationMessage(object):

    @property
    def message_type(self) -> RegistrationMessageType:
        return self._message_type

    @property
    def agent(self) -> str:
        return self._agent

    def __init__(self, message_type: RegistrationMessageType, agent: str | AgentType):
        self._message_type = message_type
        self._agent = agent.type if isinstance(agent, AgentType) else agent

    def to_dict(self) -> Dict[str, str]:
        return {
            "message_type": self._message_type.value,
            "agent": self._agent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'RegistrationMessage':
        return cls(
            message_type=RegistrationMessageType(data["message_type"]),
            agent= data["agent"]
        )
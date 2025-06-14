from asyncio import Event
from typing import Any
from dataclasses import dataclass
from autogen_core import RoutedAgent, message_handler, MessageContext, BaseAgent


@dataclass
class MessageType: ...

@dataclass
class ContentMessage:
    content: str

class NoopAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("A no op agent")

    async def on_message_impl(self, message: Any, ctx: MessageContext) -> Any:
        raise NotImplementedError

class LoopbackAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("A loop back agent.")
        self.num_calls = 0
        self.received_messages: list[Any] = []
        self.event = Event()

    @message_handler
    async def on_new_message(
        self, message: MessageType | ContentMessage, ctx: MessageContext
    ) -> MessageType | ContentMessage:
        self.num_calls += 1
        self.received_messages.append(message)
        self.event.set()
        return message
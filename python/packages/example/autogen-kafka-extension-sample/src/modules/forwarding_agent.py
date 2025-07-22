from typing import Any

from autogen_core import BaseAgent, MessageContext, AgentId


class ForwardingAgent(BaseAgent):

    def __init__(self, recipient: str):
        super().__init__(description="Forwarding agent to send messages to a specific recipient.")
        self.recipient = recipient

    async def on_message_impl(self, message: Any, ctx: MessageContext) -> Any:
        return await self.send_message(message = message,
                                       recipient=AgentId(type=self.recipient, key="default"),)
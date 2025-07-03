import logging
import pathlib
from abc import ABC, abstractmethod
from typing import TypeVar

from autogen_core import Agent, AgentRuntime, try_get_known_serializers_for_type, AgentId

from autogen_kafka_extension import KafkaStreamingAgent, KafkaAgentConfig
from packages.exemple.events import SentimentResponse, SentimentRequest

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=AgentRuntime)

class Sample(ABC):

    def __init__(self, runtime: T):
        self._agent_config = KafkaAgentConfig.from_file(f"{pathlib.Path(__file__).parent.resolve()}/config.yml")
        self._runtime = runtime

    def is_running(self) -> bool:
        return self._runtime is not None and self._runtime.is_running()

    async def new_agent(self) -> Agent:
        """Create a new agent instance."""
        agent =  KafkaStreamingAgent(
            config=self._agent_config,
            description="An example agent for sentiments analysis.",
            response_type=SentimentResponse,
            request_type=SentimentRequest,
        )

        await agent.start()
        await agent.wait_for_streams_to_start()

        return agent

    async def start(self):
        await self._start()

        self._runtime.add_message_serializer(serializer=try_get_known_serializers_for_type(SentimentRequest))
        self._runtime.add_message_serializer(serializer=try_get_known_serializers_for_type(SentimentResponse))
        await self._runtime.register_factory("sentiment_agent", lambda: self.new_agent())

    async def get_sentiment(self, text: str) -> SentimentResponse:
        if self._runtime is None:
            raise RuntimeError("Agent is not started. Call start() before using this method.")

        logger.info(f"Getting sentiment for text: {text}")
        response = await self._runtime.send_message(message=SentimentRequest(text),
                                                    recipient=AgentId(type="sentiment_agent",
                                                                      key="default"))

        return response

    @abstractmethod
    async def _start(self):
        ...


    @abstractmethod
    async def stop(self):
        ...

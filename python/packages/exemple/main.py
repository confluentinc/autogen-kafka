import logging
import pathlib
from dataclasses import dataclass

import aiorun
from autogen_core import Agent, AgentId
from autogen_core._serialization import try_get_known_serializers_for_type

from autogen_kafka_extension import KafkaAgentConfig, KafkaStreamingAgent, KafkaAgentRuntime, KafkaAgentRuntimeConfig

logger = logging.getLogger(__name__)

@dataclass
class SentimentRequest:
    text: str

class Exemple:
    def __init__(self):
        self._agent_config = KafkaAgentConfig.from_file(f"{pathlib.Path(__file__).parent.resolve()}/config.yml")
        self._runtime_config = KafkaAgentRuntimeConfig.from_file(f"{pathlib.Path(__file__).parent.resolve()}/config.yml")

        self._runtime = KafkaAgentRuntime(config=self._runtime_config)

    async def new_agent(self) -> Agent:
        """Create a new agent instance."""
        return KafkaStreamingAgent(
            config=self._agent_config,
            description="An example agent for sentiments analysis.",
        )

    async def start(self):
        await self._runtime.start_and_wait_for()

        self._runtime.add_message_serializer(serializer=try_get_known_serializers_for_type(SentimentRequest))
        await self._runtime.register_factory("sentiment_agent", lambda: self.new_agent())


    async def stop(self):
        if self._runtime is not None:
            logger.info("Stopping runtime...")
            await self._runtime.stop()

    async def get_sentiment(self, text: str) -> str:
        if self._runtime is None:
            raise RuntimeError("Agent is not started. Call start() before using this method.")

        logger.info(f"Getting sentiment for text: {text}")
        response = await self._runtime.send_message(message=SentimentRequest(text),
                                                    recipient=AgentId(type="sentiment_agent",
                                                                      key="default"))

        return response


async def start():
    logging.basicConfig(level=logging.INFO)

    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info("Starting Exemple instance...")
    exemple = Exemple()
    await exemple.start()
    logger.info("Exemple instance started successfully.")

    sentiment = await exemple.get_sentiment("This is a good example.")

    logger.info(f"Sentiment analysis result: {sentiment}")

async def shutdown(loop):
    logger.info("Shutting down Exemple instance...")
    await Exemple().stop()
    logger.info("Exemple instance stopped successfully.")

if __name__ == "__main__":
    aiorun.run(start(), stop_on_unhandled_errors=True, shutdown_callback=shutdown)
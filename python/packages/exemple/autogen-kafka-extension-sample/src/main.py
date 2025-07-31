import logging
import pathlib

import aiorun
from autogen_core import Agent, try_get_known_serializers_for_type, AgentId

from autogen_kafka_extension import KafkaAgentRuntimeFactory, KafkaStreamingAgent, KafkaAgentConfig, KafkaAgentRuntime
from src.modules import SentimentRequest, SentimentResponse
from src.modules.forwarding_agent import ForwardingAgent

logger = logging.getLogger(__name__)

class Application:

    def __init__(self):
        self.flink_runtime : KafkaAgentRuntime | None = None
        self.forwarder_runtime: KafkaAgentRuntime | None = None

    async def start(self):
        text = input("Do you want to enable logs (Y/n):")
        if text != "n" and text != "N":
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)

        print("[+] Create and start Flink runtime instance...")
        self.flink_runtime = await KafkaAgentRuntimeFactory.create_runtime_from_file(f"{pathlib.Path(__file__).parent.resolve()}/config_worker1.yml")
        print("[+] Flink runtime instance created successfully.")
        print("[+] Create and start Forwarding runtime instance...")
        self.forwarder_runtime = await KafkaAgentRuntimeFactory.create_runtime_from_file(f"{pathlib.Path(__file__).parent.resolve()}/config_worker2.yml")
        print("[+] Forwarding runtime instance created successfully.")

        print("[+] Registering Flink runtime agent and serializers...")
        self.flink_runtime.add_message_serializer(serializer=try_get_known_serializers_for_type(SentimentRequest))
        self.flink_runtime.add_message_serializer(serializer=try_get_known_serializers_for_type(SentimentResponse))
        await self.flink_runtime.register_factory("sentiment_flink", lambda: self.new_flink_agent())
        print("[+] Flink runtime agent and serializers registered successfully.")

        print("[+] Registering Forwarding runtime agent and serializers...")
        self.forwarder_runtime.add_message_serializer(serializer=try_get_known_serializers_for_type(SentimentRequest))
        self.forwarder_runtime.add_message_serializer(serializer=try_get_known_serializers_for_type(SentimentResponse))
        await self.forwarder_runtime.register_factory("sentiment_forwarder", lambda: self.new_forwarder_agent())
        print("[+] Forwarding runtime agent and serializers registered successfully.")

        text: str = ""
        while text != "exit":
            text = input("Please specify a text to analyze or type 'exit' to quit the application:")

            if text == "exit":
                break

            print(f"Analyzing sentiment for text: {text}")
            sentiment = await self.forwarder_runtime.send_message(message=SentimentRequest(text),
                                                                  recipient=AgentId(type="sentiment_forwarder",
                                                                                    key="default"))
            print(f"Sentiment analysis result: {sentiment.sentiment}")

        await self.flink_runtime.stop()
        await self.forwarder_runtime.stop()
        exit()

    async def shutdown(self, loop):
        logger.info("Shutting down instance...")
        if self.flink_runtime and self.flink_runtime.is_started:
            await self.flink_runtime.stop()
        if self.forwarder_runtime and self.flink_runtime.is_started:
            await self.forwarder_runtime.stop()
        logger.info("Instance stopped successfully.")

    @staticmethod
    async def new_forwarder_agent() -> Agent:
        print("[+] Creating a new Forwarding agent instance...")
        return ForwardingAgent("sentiment_flink")

    @staticmethod
    async def new_flink_agent() -> Agent:
        print("[+] Creating a new Flink agent instance...")

        agent_config = KafkaAgentConfig.from_file(f"{pathlib.Path(__file__).parent.resolve()}/agent_config.yml")

        """Create a new agent instance."""
        agent = KafkaStreamingAgent(
            config=agent_config,
            description="An example agent for sentiments analysis.",
            request_type=SentimentRequest,
            response_type=SentimentResponse,
        )

        await agent.start()
        await agent.wait_for_streams_to_start()

        return agent

if __name__ == "__main__":
    app: Application = Application()
    aiorun.run(app.start(), stop_on_unhandled_errors=True, shutdown_callback=app.shutdown)
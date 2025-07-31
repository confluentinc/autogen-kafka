import logging
import pathlib

import aiorun

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core.memory import MemoryQueryResult, MemoryContent, MemoryMimeType
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogen_kafka_extension import KafkaMemory

logger = logging.getLogger(__name__)

class Application:

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        pass

    async def start(self):
        logger.info("Starting application...")

        # Initialize user memory
        user_memory = KafkaMemory.create_from_file(filename=f"{pathlib.Path(__file__).parent.resolve()}/memory_config.yml",
                                                   session_id="user",
                                                   instance_id = "user_memory")
        await user_memory.start_and_wait_for()

        result : MemoryQueryResult = await user_memory.query(query="The weather should be in metric units")
        if result and result.results and len(result.results) > 0:
            logger.info(f"Memory query result: {result}")
        else:
            logger.info("No results found in memory.")

            # Add user preferences to memory
            await user_memory.add(
                MemoryContent(content="The weather should be in metric units", mime_type=MemoryMimeType.TEXT))

            await user_memory.add(MemoryContent(content="Meal recipe must be vegan", mime_type=MemoryMimeType.TEXT))

        async def get_weather(city: str, units: str = "imperial") -> str:
            if units == "imperial":
                return f"The weather in {city} is 73 °F and Sunny."
            elif units == "metric":
                return f"The weather in {city} is 23 °C and Sunny."
            else:
                return f"Sorry, I don't know the weather in {city}."

        assistant_agent = AssistantAgent(
            name="assistant_agent",
            model_client=OpenAIChatCompletionClient(
                model="gpt-4o-mini",
            ),
            tools=[get_weather],
            memory=[user_memory],
        )

        # Run the agent with a task.
        stream = assistant_agent.run_stream(task="What is the weather in New York?")
        await Console(stream)

    async def shutdown(self, loop):
        pass

if __name__ == "__main__":
    app: Application = Application()
    aiorun.run(app.start(), stop_on_unhandled_errors=True, shutdown_callback=app.shutdown)
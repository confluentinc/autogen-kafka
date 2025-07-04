import logging
import pathlib

from autogen_kafka_extension import KafkaAgentRuntimeConfig, KafkaAgentRuntime
from .sample import Sample

logger = logging.getLogger(__name__)


class KafkaSample(Sample):
    def __init__(self):
        config = KafkaAgentRuntimeConfig.from_file(f"{pathlib.Path(__file__).parent.resolve()}/config.yml")
        runtime = KafkaAgentRuntime(config=config)

        super().__init__(runtime = runtime)

    async def _start(self):
        await self._runtime.start_and_wait_for()

    async def stop(self):
        if self._runtime is not None:
            logger.info("Stopping runtime...")
            await self._runtime.stop()
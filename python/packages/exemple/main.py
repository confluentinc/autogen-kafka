import logging

import aiorun
from packages.exemple.grpcs_sample import GRPCSample
from packages.exemple.kafka_sample import KafkaSample

logger = logging.getLogger(__name__)


class Application:

    def __init__(self):
        self.exemple = None

    async def start(self):
        logging.basicConfig(level=logging.INFO)

        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logger.info("Starting Exemple instance...")
        # self.exemple = GRPCSample()
        self.exemple = KafkaSample()
        await self.exemple.start()
        logger.info("Exemple instance started successfully.")

        sentiment = await self.exemple.get_sentiment("This is a good example.")

        logger.info(f"Sentiment analysis result: {sentiment.sentiment}")

        sentiment = await self.exemple.get_sentiment("This is a bad example.")

        logger.info(f"Sentiment analysis result: {sentiment.sentiment}")

    async def shutdown(self, loop):
        logger.info("Shutting down Exemple instance...")
        await self.exemple.stop()
        logger.info("Exemple instance stopped successfully.")

if __name__ == "__main__":
    app: Application = Application()
    aiorun.run(app.start(), stop_on_unhandled_errors=True, shutdown_callback=app.shutdown)
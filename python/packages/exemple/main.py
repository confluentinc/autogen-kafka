import logging

import aiorun
from packages.exemple.grpcs_sample import GRPCSample
from packages.exemple.kafka_sample import KafkaSample
from packages.exemple.sample import Sample

logger = logging.getLogger(__name__)


class Application:

    def __init__(self):
        self.exemple : Sample | None = None

    async def start(self):
        text = input("Do you want to enable logs (y/N):")
        if text == "y":
            logging.basicConfig(level=logging.ERROR)

            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        text = input("Select the runtime to use: Kafka or GRPC (Default: Kafka)?")
        if text == "GRPC":
            self.exemple = GRPCSample()
        else:
            self.exemple = KafkaSample()

        logger.info("Starting Exemple instance...")
        await self.exemple.start()
        logger.info("Exemple instance started successfully.")



        text: str = ""
        while text != "exit":
            text = input("Please specify a text to analyze or type 'exit' to quit the application:")

            if text == "exit":
                break

            print(f"Analyzing sentiment for text: {text}")
            sentiment = await self.exemple.get_sentiment(text)
            print(f"Sentiment analysis result: {sentiment.sentiment}")

        await self.exemple.stop()
        quit()

    async def shutdown(self, loop):
        logger.info("Shutting down Exemple instance...")
        if self.exemple and self.exemple.is_running:
            await self.exemple.stop()
        logger.info("Exemple instance stopped successfully.")

if __name__ == "__main__":
    app: Application = Application()
    aiorun.run(app.start(), stop_on_unhandled_errors=True, shutdown_callback=app.shutdown)
import logging

import aiorun
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

from autogen_kafka_extension.worker_config import WorkerConfig
from autogen_kafka_extension.worker_runtime import KafkaWorkerAgentRuntime

config: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                    registry_topic="autogent_comm",
                                    request_topic="autogent_in",
                                    response_topic="autogent_out",
                                    bootstrap_servers=["pkc-419q3.us-east4.gcp.confluent.cloud:9092"],
                                    security_protocol=SecurityProtocol.SASL_SSL,
                                    security_mechanism=SaslMechanism.PLAIN,
                                    sasl_plain_username="PX23FOY42OQWYTWQ",
                                    sasl_plain_password="8rPLzejOqwk5U8TNCX8y/6D/ByWUSN2XX33qbP8rt6blyFH9v+kktoICjdTw/gJ8",
                                    group_id="autogen-group_1",
                                    client_id="autogen-client_1")

worker: KafkaWorkerAgentRuntime = KafkaWorkerAgentRuntime(config)

async def stop(loop) -> None:
    """
    Shutdown callback to clean up resources when the worker stops.
    This function is called when the worker runtime is stopped.
    """
    await worker.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    aiorun.run(worker.start(), stop_on_unhandled_errors=True, shutdown_callback=stop)

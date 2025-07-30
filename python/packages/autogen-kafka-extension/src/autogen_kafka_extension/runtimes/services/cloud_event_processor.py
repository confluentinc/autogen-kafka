from azure.core.messaging import CloudEvent

from autogen_kafka_extension import KafkaAgentRuntimeConfig
from autogen_kafka_extension.runtimes.services.message_processor import MessageProcessor
from autogen_kafka_extension.shared.message_producer import MessageProducer
from autogen_kafka_extension.shared.stream import ConsumerRecord, Stream
from autogen_kafka_extension.shared.streaming_worker_base import StreamingWorkerBase


class CloudEventProcessor(StreamingWorkerBase[KafkaAgentRuntimeConfig]):
    """
    A class to process cloud events.
    """

    def __init__(self,
                 config: KafkaAgentRuntimeConfig,
                 message_processor: MessageProcessor):
        super().__init__(config=config,
                         target_type=CloudEvent,
                         topic=config.publish_topic)
        self._message_processor = message_processor

    async def handle_event(self, record: ConsumerRecord, stream: Stream, producer: MessageProducer) -> None:
        """Callback for processing incoming Kafka records.

        Processes incoming Kafka consumer records by routing them to the appropriate
        message processor based on the event type. Handles both RequestEvents
        and CloudEvents.

        Args:
            cr: The Kafka ConsumerRecord containing the message data and metadata.
            stream: The Kafka stream instance for stream processing operations.
            producer: The send function for producing messages back to Kafka topics.
        """
        event: CloudEvent = record.value

        # Use the message processor to handle the event
        await self._message_processor.process_event(event)
from azure.core.messaging import CloudEvent

from autogen_kafka import KafkaAgentRuntimeConfig
from autogen_kafka.runtimes.services.message_processor import MessageProcessor
from autogen_kafka.shared.streaming_worker_base import StreamingWorkerBase
from autogen_kafka.shared.stream import ConsumerRecord, Stream
from autogen_kafka.shared.message_producer import MessageProducer

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

    async def _handle_event(self, cr: ConsumerRecord, stream: Stream, send: Send) -> None:
        """Callback for processing incoming Kafka records.

        Processes incoming Kafka consumer records by routing them to the appropriate
        message processor based on the event type. Handles both RequestEvents
        and CloudEvents.

        Args:
            cr: The Kafka ConsumerRecord containing the message data and metadata.
            stream: The Kafka stream instance for stream processing operations.
            send: The send function for producing messages back to Kafka topics.
        """
        event: CloudEvent = cr.value

        # Use the message processor to handle the event
        await self._message_processor.process_event(event)
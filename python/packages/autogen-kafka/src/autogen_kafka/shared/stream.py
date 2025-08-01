import asyncio
import logging
import threading
from abc import ABC
from typing import Dict, Any

from confluent_kafka import Consumer, Message, KafkaException

from .message_producer import MessageProducer
from .consumer_record import ConsumerRecord
from .events import EventDeserializer, EventSerializer
from .background_task_manager import BackgroundTaskManager
from ..config.kafka_config import KafkaConfig

logger = logging.getLogger(__name__)

class EventHandler(ABC):
    async def handle_exception(self, exception: Exception, stream: 'Stream', producer: 'MessageProducer'):
        """Handle exceptions that occur during event processing."""
        logger.error(f"Exception in stream '{stream.topic}': {exception}")
        # Optionally, you can send an error message to a specific topic or log it
        # await producer.send_error_message(exception, stream._topic)
    async def handle_event(self, record: 'ConsumerRecord', stream: 'Stream', producer: 'MessageProducer'):
        """Process a ConsumerRecord and send it using the provided send function."""
        raise NotImplementedError("Subclasses must implement this method")

class Stream:

    def __init__(self,
                 config: KafkaConfig,
                 topic: str,
                 stream_processor: EventHandler,
                 deserializer: EventDeserializer,
                 producer: MessageProducer,
                 *,
                 timeout: float = 0.100):
        self._timeout = timeout
        self._topic = topic
        self._config = config

        consumer_config = config.get_consumer_config(topic)
        # consumer_config["commit.interval.ms"] = 100  # Set commit interval to 1 second
        consumer_config["enable.auto.commit"] = False  # Disable auto-commit to control when

        self._reset_offsets = consumer_config["auto.offset.reset"] is not None
        self._consumer: Consumer = Consumer(consumer_config)
        self._stream_func = stream_processor
        self._deserializer = deserializer
        self._producer = producer
        self._background_task_manager = BackgroundTaskManager()

        self._running_event = threading.Event()
        self._queue: asyncio.Queue = asyncio.Queue()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self):
        """Start the Kafka poll loop in a background thread and the processing loop in asyncio."""
        logger.info(f"Starting consumer for topic '{self._topic}'")
        self._loop = asyncio.get_event_loop()
        self._running_event.set()

        self._consumer.subscribe([self._topic])
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

        asyncio.create_task(self._process_loop())

    def _poll_loop(self):
        """Blocking Kafka poll loop in background thread."""
        try:
            while self._running_event.is_set():
                msg = self._consumer.poll(self._timeout)
                if self._reset_offsets:
                    topic_partitions_offset = self._config.utils().get_offset_for_topic(self._topic)
                    topic_partitions = list(topic_partitions_offset.keys())
                    for topic_partition in topic_partitions:
                        watermark = self._consumer.get_watermark_offsets(topic_partition)
                        if watermark[1] > 0:
                            topic_partition.offset = 0
                            # self._consumer.seek(topic_partition)
                    self._consumer.assign(topic_partitions)
                    self._reset_offsets = False
                    continue

                if msg is None:
                    continue
                if msg.error():
                    asyncio.run_coroutine_threadsafe(
                        self._process_exception(msg),
                        self._loop
                    )
                else:
                    asyncio.run_coroutine_threadsafe(self._queue.put(msg), self._loop)
        except Exception as e:
            logger.error(f"Error in polling loop for topic '{self._topic}': {e}")
        finally:
            self._consumer.close()
            logger.info(f"Consumer for topic '{self._topic}' closed")

    async def _process_exception(self, msg: Message):
        await self._stream_func.handle_exception(
            KafkaException(msg.error()),
            self,
            self._producer
        )
        # Commit the offset for the failed message so it's not reprocessed immediately
        self._consumer.commit(asynchronous=False)

    async def _process_loop(self):
        """Async processing loop that consumes messages from the queue and commits when empty."""
        try:
            had_messages = False
            while self._running_event.is_set():
                if not self._queue.empty():
                    msg: Message = await self._queue.get()
                    await self.process_message(msg)
                    # self._background_task_manager.add_task(self.process_message(msg),
                    #                                        name=f"Process message for topic {self._topic}")
                    had_messages = True
                else:
                    if had_messages:
                        # If the queue is empty, commit the offsets of processed messages
                        try:
                            self._consumer.commit(asynchronous=False)
                            logger.debug(f"Committed offsets for topic '{self._topic}' as queue is empty.")
                        except KafkaException as e:
                            logger.error(f"Failed to commit offsets for topic '{self._topic}': {e}")

                    had_messages = False
                    # Give control back to the event loop for a moment before rechecking
                    await asyncio.sleep(self._timeout) # Small sleep to prevent busy-waiting
        except Exception as e:
            logger.error(f"Error in processing loop for topic '{self._topic}': {e}")

    async def process_message(self, msg: Message):
        value = self._deserializer.deserialize(msg)
        record = ConsumerRecord(
            topic=msg.topic(),
            partition=msg.partition(),
            offset=msg.offset(),
            key=msg.key(),
            value=value,
            headers=dict(msg.headers()) if msg.headers() else {}
        )
        await self._stream_func.handle_event(record, self, self._producer)
        # No commit here, it's handled in _process_loop

    async def stop(self):
        """Stop the stream gracefully."""
        logger.info(f"Stopping consumer for topic '{self._topic}'")
        self._running_event.clear()
        if self._thread is not None:
            self._thread.join(timeout=self._timeout * 10)
            self._thread = None
        # Perform a final commit when stopping to ensure all processed messages are acknowledged
        try:
            self._consumer.commit(asynchronous=False)
            logger.info(f"Final commit performed for topic '{self._topic}' during shutdown.")
        except KafkaException as e:
            logger.error(f"Failed to perform final commit for topic '{self._topic}': {e}")
        logger.info(f"Stream for topic '{self._topic}' has stopped")

    async def send(self,
                   topic: str,
                   key: bytes,
                   value: Any,
                   serializer: EventSerializer,
                   *,
                   headers: Dict[str, Any] = None):
        return await self._producer.send(topic, key, value, serializer, headers=headers)

    @property
    def is_running(self) -> bool:
        return self._running_event.is_set()

    @property
    def topic(self) -> str:
        return self._topic
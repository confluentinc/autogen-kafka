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
        self._running = False
        self._timeout = timeout
        self._topic = topic
        self._consumer : Consumer = Consumer(config.get_consumer_config())
        self._running_lock = threading.Lock()
        self._thread : threading.Thread | None = None
        self._stream_func = stream_processor
        self._deserializer = deserializer
        self._producer = producer
        self._background_task_manager = BackgroundTaskManager()

    def start(self):
        """Start the stream's consumer."""
        if self._consumer is None:
            raise RuntimeError("Consumer is not initialized")
        logger.info(f"Starting consumer for topic '{self._topic}'")
        asyncio.create_task(self._consumer_loop())

    async def _consumer_loop(self):
        try:
            logger.info(f"Starting consumer loop for topic '{self._topic}'")
            with self._running_lock:
                self._consumer.subscribe([self._topic])
                self._running = True

            while True:
                with self._running_lock:
                    if not self._running:
                        break

                msg: Message = await asyncio.to_thread(self._consumer.poll, timeout=self._timeout)
                if msg is None:
                    continue
                if msg.error():
                    self._background_task_manager.add_task(
                        self._stream_func.handle_exception(
                            exception=KafkaException(msg.error()),
                            stream=self,
                            producer=self._producer)
                    )
                    continue

                self._background_task_manager.add_task(self.process_message(msg))
        except Exception as e:
            logger.error(f"Error in consumer loop for topic '{self._topic}': {e}")
            raise e

        finally:
            logger.info(f"Stopping consumer loop for topic '{self._topic}'")
            # Close down consumer to commit final offsets.
            self._consumer.close()
            logger.info(f"Consumer loop for topic '{self._topic}' stopped")

    async def process_message(self, msg: Message):
        value = self._deserializer.deserialize(msg)
        record: ConsumerRecord = ConsumerRecord(
            topic=msg.topic(),
            partition=msg.partition(),
            offset=msg.offset(),
            key=msg.key(),
            value=value,
            headers=dict(msg.headers()) if msg.headers() else {}
        )
        await self._stream_func.handle_event(
            record=record,
            stream=self,
            producer=self._producer
        )

    async def stop(self):
        """Stop the stream's consumer."""
        with self._running_lock:
            if self._running:
                logger.info(f"Stopping consumer for topic '{self._topic}'")
                self._running = False
            else:
                logger.warning(f"Consumer for topic '{self._topic}' is already stopped")

        if self._thread is not None:
            self._thread.join(timeout=self._timeout*10)
            self._thread = None

    async def send(self,
                   topic: str,
                   key: bytes,
                   value: Any,
                   serializer: EventSerializer,
                    *,
                   headers: Dict[str, Any] = None):
        return self._producer.send(topic, key, value, serializer, headers=headers)

    @property
    def is_running(self) -> bool:
        with self._running_lock:
            return self._running

    @property
    def topic(self):
        return self._topic

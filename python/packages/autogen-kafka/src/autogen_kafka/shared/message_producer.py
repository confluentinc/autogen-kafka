import asyncio
import logging
from typing import Any, Dict

from confluent_kafka import Producer

from .background_task_manager import BackgroundTaskManager
from .events import EventSerializer

logger = logging.getLogger(__name__)

def acked(err, msg):
    if err is not None:
        logger.error("Failed to deliver message: %s: %s" % (str(msg), str(err)))

class MessageProducer:
    """
    A class to handle message production for Kafka topics.
    """

    def __init__(self, config):
        self._background_task_manager = BackgroundTaskManager()
        self._producer = Producer(config)
        self._loop = asyncio.get_running_loop()

    async def send(self,
                   topic: str,
                   key: bytes,
                   value: Any,
                   serializer: EventSerializer,
                    *,
                   headers: Dict[str, Any] = None):
        # Serialize the value using the provided serializer
        serialized_value = await serializer.serialize(
            payload=value,
            headers=headers
        )

        async def send_async():
            self._producer.produce(
                topic=topic,
                key=key,
                value=serialized_value,
                headers=headers,
                on_delivery=acked
            )
            self._producer.flush()

        self._background_task_manager.add_task(
            coro = send_async(),
            name=f"Send to topic {topic}")

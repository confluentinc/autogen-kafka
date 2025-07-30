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

        self._background_task_manager.add_task(
            self._send_async(
                topic=topic,
                key=key,
                value=serialized_value,
                headers=headers)
        )

    async def _send_async(self, topic, key, value, headers):
        self._producer.produce(
            topic=topic,
            key=key,
            value=value,
            headers=headers,
            callback=acked)
        self._producer.poll(1)

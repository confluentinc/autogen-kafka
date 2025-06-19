import asyncio
import logging
import uuid
from typing import Any

from autogen_core import CancellationToken
from autogen_core.memory import Memory, UpdateContextResult, MemoryContent, MemoryQueryResult, ListMemory
from autogen_core.model_context import ChatCompletionContext
from kstreams import Stream, Send, ConsumerRecord

from autogen_kafka_extension.memory.memory_config import MemoryConfig
from autogen_kafka_extension.shared.streaming_worker_base import StreamingWorkerBase
from autogen_kafka_extension.shared.events.memory_event import MemoryEvent
from autogen_kafka_extension.shared.topic_admin_service import TopicAdminService

logger = logging.getLogger(__name__)

# This is experimental and may change in the future.
class KafkaMemory(Memory, StreamingWorkerBase):

    @property
    def memory_topic(self) -> str:
        """Get the topic name for this memory instance."""
        return self._memory_topic

    def __init__(self,
                 config: MemoryConfig,
                 session_id: str,
                 *,
                 memory: Memory | None = None) -> None:
        self._config = config
        self._memory_topic = config.memory_topic + "_" + session_id
        self._session_id = session_id
        self._memory = memory or ListMemory()
        self._id = uuid.uuid4().__str__()

        StreamingWorkerBase.__init__(
            self,
            config=config,
            topic=self._memory_topic)

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> UpdateContextResult:
        return await self._memory.update_context(model_context = model_context)

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        await self._ensure_started()

        return await self._memory.query(
            query=query,
            cancellation_token=cancellation_token,
            **kwargs,
        )

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        await self._ensure_started()

        await self._memory.add(content, cancellation_token=cancellation_token)
        await super().send_message(
            message=MemoryEvent(memory_content=content, sender=self._id),
            topic=self.memory_topic,
            recipient=self._session_id,
        )

    async def clear(self) -> None:

        await self._memory.clear()

        if self.is_started:
            await self.stop()

        # Delete the memory topic
        topic_admin = TopicAdminService(config=self._config)
        topic_admin.delete_topics(topic_names=[self.memory_topic])

        # TODO: Find a better way to wait for topic deletion
        while self.memory_topic in topic_admin.list_topics():
            logger.info(f"Waiting for topic {self.memory_topic} to be deleted...")
            await asyncio.sleep(1)

        await self.start()

    async def close(self) -> None:
        await self._memory.close()
        await self.stop()

    async def _ensure_started(self) -> None:
        if not self.is_started:
            await super().start()
            logger.info(f"KafkaMemory worker started with ID: {self._session_id}")

    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
        if record.value is None:
            # Received a tombstone record, which indicates deletion
            logger.debug(f"Received tombstone record: {record}")
            if not str(record.key).startswith(self._session_id):
                logger.debug("Tombstone record from another worker, clearing memory")
                await self._memory.clear()
            return

        if not isinstance(record.value, MemoryEvent):
            logger.error(f"Unexpected record value type: {type(record.value)}")
            return

        # Process the memory content
        event = record.value
        if event.sender == self._id:
            logger.debug(f"Skipping event from self: {event}")
            return

        await self._memory.add(event.memory_content)
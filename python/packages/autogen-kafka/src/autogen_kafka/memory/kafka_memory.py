import asyncio
import logging
import uuid
from typing import Any, Optional, Dict

from autogen_core import CancellationToken
from autogen_core.memory import Memory, UpdateContextResult, MemoryContent, MemoryQueryResult, ListMemory
from autogen_core.model_context import ChatCompletionContext

from ..config.services.kafka_utils import KafkaUtils
from ..config.memory_config import KafkaMemoryConfig
from ..shared import MessageProducer
from ..shared.events.events_serdes import EventSerializer
from ..shared.helpers import Helpers
from ..shared.stream import ConsumerRecord, Stream
from ..shared.streaming_worker_base import StreamingWorkerBase
from ..shared.events.memory_event import MemoryEvent

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TOPIC_DELETION_WAIT_SECONDS = 1.0
MAX_TOPIC_DELETION_RETRIES = 30
TOPIC_DELETION_TIMEOUT_SECONDS = 60.0


class KafkaMemoryError(Exception):
    """Base exception for KafkaMemory operations."""
    pass


class TopicDeletionTimeoutError(KafkaMemoryError):
    """Raised when topic deletion times out."""
    pass


class KafkaMemory(Memory, StreamingWorkerBase[KafkaMemoryConfig]):
    """
    A distributed memory implementation that uses Apache Kafka for persistence and synchronization.
    
    This class provides a memory interface that persists content to Kafka topics, allowing multiple
    instances to share memory state across distributed systems. It wraps an underlying Memory instance
    (defaults to ListMemory) and publishes all memory operations to a Kafka topic for synchronization.
    
    Key features:
    - Distributed memory sharing across multiple instances
    - Persistent storage via Kafka topics
    - Session-based topic isolation
    - Automatic topic management (creation/deletion)
    - Event-driven synchronization between instances
    - Async context manager support for proper resource cleanup
    
    This implementation is experimental and subject to change.
    """

    def __init__(self,
                 config: KafkaMemoryConfig,
                 session_id: str,
                 *,
                 memory: Memory | None = None,
                 instance_id: str | None = None) -> None:
        """
        Initialize a KafkaMemory instance.
        
        Args:
            config (MemoryConfig): Configuration object containing Kafka connection details
                                  and memory-specific settings.
            session_id (str): Unique identifier for this memory session. Used to create
                            an isolated topic and identify messages from this instance.
            memory (Optional[Memory]): Underlying memory implementation to wrap.
                                     Defaults to ListMemory() if not provided.
        """
        self._config = config
        self._session_id = session_id
        self._memory_topic = self._create_topic_name(config.memory_topic, session_id)
        self._memory = memory or ListMemory()
        self._instance_id = instance_id or str(uuid.uuid4())
        self._serializer = EventSerializer(
            topic=self._memory_topic,
            source_type=MemoryEvent,
            kafka_utils=config.kafka_config.utils()
        )

        # Create topic
        config.kafka_config.utils().create_topic(self._memory_topic)

        # Initialize the streaming worker base with the memory topic
        StreamingWorkerBase.__init__(
            self,
            config=config,
            topic=self._memory_topic,
            target_type=MemoryEvent)

        try:
            offsets = config.kafka_config.utils().get_offset_for_topic(self._memory_topic)

            self._offsets : Dict[int, int] = {}
            for topic_partition in offsets:
                offset = offsets[topic_partition].offset
                if offset == 0:
                    continue
                partition = topic_partition.partition
                self._offsets[partition] = offset - 1

        except Exception as e:
            logger.error(f"Failed to get offset for topic {self._memory_topic}: {e}")
            raise KafkaMemoryError(f"Failed to get offset for topic {self._memory_topic}: {e}") from e

        self._initialized = len(self._offsets) == 0

    async def start_and_wait_for(self, timeout : int = 30):
        """
        Start the Kafka stream processing engine and wait for background tasks to start.
        :param timeout: The timeout in seconds.

        Initializes and starts all internal services in the correct order:
        1. Subscription service for managing agent subscriptions
        2. Messaging client for sending/receiving messages
        3. Agent registry for agent discovery and management
        4. Underlying streaming service for Kafka connectivity
        5. Wait for all background tasks to start.

        This method is idempotent - calling it multiple times has no additional effect.
        """
        if self.is_started:
            return

        await self.start()
        await self.wait_for_streams_to_start(timeout=timeout)
        await Helpers.wait_for_condition(check_func=self._is_initialized, timeout=timeout, check_interval=0.1)

    async def _is_initialized(self) -> bool :
        """
        Check if the KafkaMemory instance is fully initialized and ready.
        :return: true if all offsets are zero, indicating that all messages have been processed.
        """
        return self._initialized

    @property
    def memory_topic(self) -> str:
        """
        Get the Kafka topic name used for this memory instance.
        
        Returns:
            str: The topic name, which includes the session ID for isolation.
        """
        return self._memory_topic

    @property
    def session_id(self) -> str:
        """
        Get the session ID for this memory instance.
        
        Returns:
            str: The session ID used for topic isolation and message identification.
        """
        return self._session_id

    @property
    def instance_id(self) -> str:
        """
        Get the unique instance ID for this memory instance.
        
        Returns:
            str: The unique ID used to identify messages from this instance.
        """
        return self._instance_id

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_started()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with proper cleanup."""
        await self.close()

    async def update_context(
        self,
        model_context: ChatCompletionContext,
    ) -> UpdateContextResult:
        """
        Update the model context with memory content.
        
        This method delegates to the underlying memory implementation to update
        the chat completion context with relevant memory content.
        
        Args:
            model_context (ChatCompletionContext): The context to update with memory content.
            
        Returns:
            UpdateContextResult: Result of the context update operation.
            
        Raises:
            KafkaMemoryError: If there's an error updating the context.
        """
        try:
            return await self._memory.update_context(model_context=model_context)
        except Exception as e:
            logger.error(f"Failed to update context: {e}")
            raise KafkaMemoryError(f"Context update failed: {e}") from e

    async def query(
        self,
        query: str | MemoryContent,
        cancellation_token: CancellationToken | None = None,
        **kwargs: Any,
    ) -> MemoryQueryResult:
        """
        Query the memory for relevant content.
        
        Ensures the Kafka worker is started before querying the underlying memory.
        
        Args:
            query (str | MemoryContent): The query to search for in memory.
            cancellation_token (Optional[CancellationToken]): Token to cancel the operation.
            **kwargs (Any): Additional keyword arguments passed to the underlying
                          memory query method.
            
        Returns:
            MemoryQueryResult: The result of the memory query.
            
        Raises:
            KafkaMemoryError: If there's an error querying the memory.
        """
        try:
            await self._ensure_started()
            return await self._memory.query(
                query=query,
                cancellation_token=cancellation_token,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"Failed to query memory: {e}")
            raise KafkaMemoryError(f"Memory query failed: {e}") from e

    async def add(self, content: MemoryContent, cancellation_token: CancellationToken | None = None) -> None:
        """
        Add content to memory and broadcast the addition to other instances.
        
        This method adds content to the local memory and then publishes a MemoryEvent
        to the Kafka topic so other KafkaMemory instances can synchronize.
        
        Args:
            content (MemoryContent): The content to add to memory.
            cancellation_token (Optional[CancellationToken]): Token to cancel the operation.
            
        Raises:
            KafkaMemoryError: If there's an error adding content or broadcasting the event.
        """
        try:
            await self._ensure_started()
            
            # Add to local memory first
            await self._memory.add(content, cancellation_token=cancellation_token)
            
            # Broadcast the addition to other instances via Kafka
            await self._broadcast_memory_event(content)
            
        except Exception as e:
            logger.error(f"Failed to add content to memory: {e}")
            raise KafkaMemoryError(f"Failed to add memory content: {e}") from e

    async def clear(self) -> None:
        """
        Clear all memory content and reset the Kafka topic.
        
        This method:
        1. Clears the local memory
        2. Stops the Kafka worker if running
        3. Deletes the memory topic to clear distributed state
        4. Waits for topic deletion to complete with timeout
        5. Restarts the worker with a clean topic
        
        This effectively resets the entire distributed memory state.
        
        Raises:
            KafkaMemoryError: If there's an error clearing memory or managing the topic.
        """
        try:
            logger.info(f"Clearing memory for session {self._session_id}")
            
            # Clear local memory first
            await self._memory.clear()
            
            # Stop the worker if it's running
            if self.is_started:
                await self.stop()
            
            # Reset the topic
            await self._reset_memory_topic()
            
            # Restart with a clean topic
            await self.start()
            
            logger.info(f"Memory cleared successfully for session {self._session_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
            raise KafkaMemoryError(f"Failed to clear memory: {e}") from e

    async def close(self) -> None:
        """
        Close the memory instance and cleanup resources.
        
        This method closes the underlying memory implementation and stops
        the Kafka worker. Should be called when the memory is no longer needed.
        
        Raises:
            KafkaMemoryError: If there's an error closing the memory or worker.
        """
        try:
            logger.info(f"Closing KafkaMemory for session {self._session_id}")
            
            # Close underlying memory
            if self._memory:
                await self._memory.close()
            
            # Stop the Kafka worker
            if self.is_started:
                await self.stop()
                
            logger.info(f"KafkaMemory closed successfully for session {self._session_id}")
            
        except Exception as e:
            logger.error(f"Failed to close memory: {e}")
            raise KafkaMemoryError(f"Failed to close memory: {e}") from e

    # Private methods

    def _create_topic_name(self, base_topic: str, session_id: str) -> str:
        """
        Create a session-specific topic name.
        
        Args:
            base_topic (str): The base topic name from configuration.
            session_id (str): The session ID for isolation.
            
        Returns:
            str: The complete topic name with session ID.
        """
        return f"{base_topic}_{session_id}"

    async def _ensure_started(self) -> None:
        """
        Ensure the Kafka worker is started before performing memory operations.
        
        This is an internal method that checks if the streaming worker is running
        and starts it if necessary. This ensures the instance can receive and send
        memory synchronization events.
        
        Raises:
            KafkaMemoryError: If the worker fails to start.
        """
        if not self.is_started:
            try:
                await super().start()
                logger.info(f"KafkaMemory worker started for session {self._session_id}")
            except Exception as e:
                logger.error(f"Failed to start KafkaMemory worker: {e}")
                raise KafkaMemoryError(f"Failed to start worker: {e}") from e

    async def _broadcast_memory_event(self, content: MemoryContent) -> None:
        """
        Broadcast a memory event to other instances.
        
        Args:
            content (MemoryContent): The memory content to broadcast.
            
        Raises:
            Exception: If broadcasting fails.
        """
        event = MemoryEvent(memory_content=content, sender=self._instance_id)
        await super().send_message(
            message=event,
            topic=self.memory_topic,
            recipient=self._session_id,
            serializer=self._serializer
        )
        logger.debug(f"Broadcasted memory event for session {self._session_id}")

    async def _reset_memory_topic(self) -> None:
        """
        Reset the memory topic by deleting and waiting for deletion completion.
        
        Raises:
            TopicDeletionTimeoutError: If topic deletion times out.
            KafkaMemoryError: If there's an error managing the topic.
        """
        try:
            kafka_utils = self._config.kafka_config.utils()

            # Delete the memory topic to clear the distributed state
            kafka_utils.delete_topics(topic_names=[self.memory_topic])
            logger.info(f"Initiated deletion of topic {self.memory_topic}")
            
            # Wait for topic deletion to complete with timeout
            await self._wait_for_topic_deletion(kafka_utils)
            
        except TopicDeletionTimeoutError:
            raise
        except Exception as e:
            logger.error(f"Failed to reset memory topic: {e}")
            raise KafkaMemoryError(f"Failed to reset topic: {e}") from e

    async def _wait_for_topic_deletion(self, kafka_utils: KafkaUtils) -> None:
        """
        Wait for topic deletion to complete with timeout and retry logic.

        Raises:
            TopicDeletionTimeoutError: If topic deletion times out.
        """
        retries = 0
        start_time = asyncio.get_event_loop().time()
        
        while self.memory_topic in kafka_utils.list_topics():
            current_time = asyncio.get_event_loop().time()
            
            # Check for overall timeout
            if current_time - start_time > TOPIC_DELETION_TIMEOUT_SECONDS:
                raise TopicDeletionTimeoutError(
                    f"Topic {self.memory_topic} deletion timed out after "
                    f"{TOPIC_DELETION_TIMEOUT_SECONDS} seconds"
                )
            
            # Check for max retries
            if retries >= MAX_TOPIC_DELETION_RETRIES:
                raise TopicDeletionTimeoutError(
                    f"Topic {self.memory_topic} deletion exceeded max retries ({MAX_TOPIC_DELETION_RETRIES})"
                )
            
            logger.debug(f"Waiting for topic {self.memory_topic} deletion... (attempt {retries + 1})")
            await asyncio.sleep(DEFAULT_TOPIC_DELETION_WAIT_SECONDS)
            retries += 1
        
        logger.info(f"Topic {self.memory_topic} successfully deleted after {retries} attempts")

    async def handle_event(self, record: ConsumerRecord, stream: Stream, producer: MessageProducer) -> None:
        """
        Handle incoming Kafka events for memory synchronization.
        
        This method processes incoming MemoryEvents from other KafkaMemory instances
        and updates the local memory accordingly. It handles two types of events:
        1. Tombstone records (null values) indicating memory clearing
        2. MemoryEvents containing content to add to memory
        
        Args:
            record (ConsumerRecord): The Kafka consumer record containing the event.
            stream (Stream): The Kafka stream object (unused in this implementation).
            producer (Send): The send object for publishing messages (unused in this implementation).
        """
        try:
            force_insert = not self._initialized
            if force_insert:
                if record.offset >= self._offsets.get(record.partition):
                    # Remove this offset from the offset map
                    del self._offsets[record.partition]

                self._initialized = len(self._offsets) == 0
                if self._initialized:
                    logger.info(f"KafkaMemory initialized for session {self._session_id} with offsets: {self._offsets}")

            if record.value is None:
                await self._handle_tombstone_record(record)
                return

            if not isinstance(record.value, MemoryEvent):
                logger.error(f"Unexpected record value type: {type(record.value)}")
                return

            await self._handle_memory_event(record.value, force_insert)
            
        except Exception as e:
            logger.error(f"Error handling Kafka event: {e}")
            # Don't re-raise to avoid breaking the event processing loop

    async def _handle_tombstone_record(self, record: ConsumerRecord) -> None:
        """
        Handle tombstone records indicating memory clearing.
        
        Args:
            record (ConsumerRecord): The tombstone record to process.
        """
        logger.debug(f"Received tombstone record: {record}")
        
        # Only clear memory if the tombstone is from another worker instance
        if not str(record.key).startswith(self._session_id):
            logger.debug("Tombstone record from another worker, clearing memory")
            await self._memory.clear()

    async def _handle_memory_event(self, event: MemoryEvent, force_insert: bool) -> None:
        """
        Handle memory events from other instances.
        
        Args:
            event (MemoryEvent): The memory event to process.
        """
        # Skip events that we sent ourselves to avoid duplicate processing
        if event.sender == self._instance_id and not force_insert:
            logger.debug(f"Skipping event from self: {event}")
            return

        # Add the content from other instances to our local memory
        logger.debug(f"Adding content from instance {event.sender}")
        await self._memory.add(event.memory_content)

    @classmethod
    def create_from_file(cls, filename: str,
                         session_id: str = uuid.uuid4().__str__(),
                         *,
                         instance_id : str | None = None) -> "KafkaMemory":
        """
        Create a KafkaMemory instance from a configuration file.

        Args:
            filename (str): Path to the configuration file.
            session_id (str): Unique session ID for this memory instance.
            instance_id (str): Unique instance ID for this memory instance. Defaults to a random UUID.

        Returns:
            KafkaMemory: An instance of KafkaMemory initialized with the provided configuration.
        """
        config = KafkaMemoryConfig.from_file(filename)
        return cls(config=config, session_id=session_id, instance_id=instance_id)
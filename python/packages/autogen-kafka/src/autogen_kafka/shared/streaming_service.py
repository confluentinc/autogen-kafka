import asyncio
import threading
from typing import Dict, Set, Any
import logging

from .events import EventSerializer
from .background_task_manager import BackgroundTaskManager
from .message_producer import MessageProducer
from .stream import Stream, EventHandler
from ..config.kafka_config import KafkaConfig
from .events.events_serdes import EventDeserializer
from ..config.streaming_config import StreamingServiceConfig

logger = logging.getLogger(__name__)



class StreamingService:

    def __init__(self, config: KafkaConfig):
        self._config = config
        self._streams : Dict[str, Stream] = {}
        self._background_task_manager = BackgroundTaskManager()

        # Stream tracking with custom TrackableStream
        self._status_lock = threading.Lock()
        try:
            self._producer = MessageProducer(config.get_producer_config())
        except Exception as e:
            logger.error(f"Failed to initialize producer: {e}")
            raise RuntimeError(f"Failed to initialize producer: {e}")

    def create_and_add_stream(self,
                              stream_config: StreamingServiceConfig,
                              func: EventHandler,
                              *,
                              schema_str: str | None = None) -> Stream:


        # Create topics if requested
        if stream_config.auto_create_topics:
            self._config.utils().create_topic(stream_config.topic)

        stream: Stream = Stream(
            config=self._config,
            topic=stream_config.topic,
            stream_processor=func,
            deserializer=EventDeserializer(
                kafka_utils=self._config.utils(),
                target_type=stream_config.target_type,
                schema_str=schema_str
            ),
            producer=self._producer,
        )

        try:
            self._streams[stream_config.name] = stream
            stream.start()
        except Exception as e:
            logger.error(f"Failed to add stream '{stream_config.name}': {e}")
            raise e

        logger.debug(f"Created stream '{stream_config.name}' for topic '{stream_config.topic}'")

        return stream

    async def start(self):
        pass

    def get_stream_names(self) -> Set[str]:
        """Get the names of all registered streams.
        
        Returns:
            Set[str]: Set of stream names that have been registered with this service.
        """
        with self._status_lock:
            return set(self._streams.keys())

    def is_stream_running(self, stream_name: str) -> bool:
        """Check if a specific stream's consumer is currently running.
        
        A stream is considered running when its underlying Kafka consumer
        has started and is actively polling for messages, regardless of whether
        it has processed any messages yet.
        
        Args:
            stream_name (str): The name of the stream to check.
            
        Returns:
            bool: True if the stream's consumer is running, False otherwise.
            
        Raises:
            KeyError: If no stream with the given name exists.
        """
        with self._status_lock:
            if stream_name not in self._streams:
                raise KeyError(f"Stream '{stream_name}' not found")
            
            stream = self._streams[stream_name]
            return stream.is_running

    def are_all_streams_running(self) -> bool:
        """Check if all registered streams' consumers are currently running.
        
        Returns:
            bool: True if all stream consumers are running, False if any consumer 
                  is not running or if no streams are registered.
        """
        with self._status_lock:
            if not self._streams:
                return False
            
            return all(stream.is_running for stream in self._streams.values())

    def get_stream_status(self) -> Dict[str, bool]:
        """Get the running status of all stream consumers.
        
        Returns:
            Dict[str, bool]: Dictionary mapping stream names to their consumer running status.
        """
        with self._status_lock:
            return {
                name: stream.is_running
                for name, stream in self._streams.items()
            }

    async def wait_for_streams_to_start(self, timeout: float = 30.0, check_interval: float = 0.1) -> bool:
        """Wait until all registered stream consumers are running.
        
        This method polls the consumer running status at regular intervals until either
        all consumers are running or the timeout is reached. It uses the custom
        TrackableStream's is_running property for reliable status checking.
        
        Args:
            timeout (float): Maximum time to wait in seconds. Defaults to 30.0 seconds.
            check_interval (float): Time between status checks in seconds. Defaults to 0.1 seconds.
            
        Returns:
            bool: True if all consumers are running within the timeout, False if timeout occurred.
            
        Raises:
            ValueError: If timeout or check_interval are negative values.
            
        Example:
            ```python
            # Wait for all streams to start before proceeding
            if await service.wait_for_streams_to_start(timeout=60.0):
                print("All streams are running!")
            else:
                print("Timeout waiting for streams to start")
            ```
        """
        if timeout < 0:
            raise ValueError("Timeout must be non-negative")
        if check_interval <= 0:
            raise ValueError("Check interval must be positive")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if self.are_all_streams_running():
                logger.info("All streams are now running")
                return True
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                stream_status = self.get_stream_status()
                running_streams = [name for name, status in stream_status.items() if status]
                not_running_streams = [name for name, status in stream_status.items() if not status]
                
                logger.warning(
                    f"Timeout waiting for streams to start after {timeout}s. "
                    f"Running: {running_streams}, Not running: {not_running_streams}"
                )
                return False
            
            await asyncio.sleep(check_interval)

    async def stop(self) -> None:
        """Stop the streaming service.
        
        This method stops the underlying StreamEngine and all associated consumers.
        """
        logger.info("Stopping streaming service")
        with self._status_lock:
            for stream in self._streams.values():
                await stream.stop()
            self._streams.clear()
        logger.info("Streaming service stopped")

    async def send(self,
                   topic: str,
                   key: bytes | str | None,
                   value: Any,
                   serializer: EventSerializer,
                    *,
                   headers: Dict[str, Any] = None) -> None:
        """Send a message to the specified topic.

        Args:
            :param topic (str): The Kafka topic to send the message to.
            :param key (bytes): The key for the message.
            :param value (Any): The value of the message.
            :param headers (Dict[str, Any], optional): Optional headers for the message.
            :param serializer: The serializer to use for the value.
        """
        await self._producer.send(
            topic=topic,
            key=key,
            value=value,
            serializer=serializer,
            headers=headers
        )
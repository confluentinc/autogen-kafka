import asyncio
import json
import logging
from asyncio import Future
from typing import Any, Mapping, Dict

from autogen_core import MessageContext, BaseAgent, JSON_DATA_CONTENT_TYPE
from autogen_core._serialization import SerializationRegistry, try_get_known_serializers_for_type
from kstreams import ConsumerRecord, Stream, Send

from ..config.agent_config import KafkaAgentConfig
from .event.agent_event import AgentEvent
from ..shared.background_task_manager import BackgroundTaskManager
from ..shared.events.events_serdes import EventSerializer
from ..shared.streaming_worker_base import StreamingWorkerBase


class KafkaStreamingAgent(BaseAgent, StreamingWorkerBase[KafkaAgentConfig]):
    """A streaming agent that communicates via Kafka topics.
    
    This agent extends BaseAgent to provide Kafka-based messaging capabilities.
    It handles message serialization/deserialization, manages pending requests,
    and coordinates with Kafka streams for distributed agent communication.
    
    The agent maintains state for request correlation and provides mechanisms
    for saving/loading state for persistence and recovery scenarios.
    
    Attributes:
        _serialization_registry: Registry for message type serialization
        _pending_requests: Dict mapping request IDs to their Future objects
        _pending_requests_lock: Async lock for thread-safe request management
        _next_request_id: Counter for generating unique request identifiers
        _background_task_manager: Manager for background async tasks
    """

    def __init__(self,
                 config: KafkaAgentConfig,
                 description: str) -> None:
        """Initialize the Kafka streaming agent.
        
        Args:
            config: Configuration object containing Kafka connection details,
                   topic names, and other agent-specific settings
            description: Human-readable description of the agent's purpose
                        and capabilities
        """
        # Initialize BaseAgent with the provided description
        BaseAgent.__init__(self, description)

        # Initialize StreamingWorkerBase with Kafka configuration
        StreamingWorkerBase.__init__(self,
                                     config=config,
                                     topic=config.request_topic,
                                     target_type=AgentEvent)
        
        # Initialize the message serialization registry for handling different message types
        self._serialization_registry = SerializationRegistry()
        
        # Dictionary to track pending requests awaiting responses
        # Key: request_id (str), Value: Future object for the response
        self._pending_requests: Dict[str, Future[Any]] = {}
        
        # Async lock to ensure thread-safe access to pending requests
        self._pending_requests_lock = asyncio.Lock()
        
        # Counter for generating unique request IDs (monotonically increasing)
        self._next_request_id = 0
        
        # Manager for handling background tasks (e.g., sending messages)
        self._background_task_manager = BackgroundTaskManager()

        # Initialize the serializer
        self._serializer = EventSerializer(
            topic=config.request_topic,
            source_type=AgentEvent,
            schema_registry_service=config.kafka_config.get_schema_registry_service()
        )

        # Start the agent
        logging.info("KafkaStreamingAgent initialized successfully.")

    async def on_message_impl(self, message: Any, ctx: MessageContext) -> Any:
        """Handle incoming messages by serializing and sending them via Kafka.
        
        This method processes incoming messages from the agent runtime, serializes
        them using the registered serialization registry, and sends them to the
        configured Kafka topic. It returns a Future that will be resolved when
        the corresponding response is received.
        
        Args:
            message: The message object to be processed and sent
            ctx: Message context containing sender information and metadata
            
        Returns:
            The response message received from the Kafka topic, deserialized
            from JSON format
            
        Raises:
            Exception: If message serialization fails or if the response
                      handling encounters an error
        """
        # Get the type name for the message for serialization registry
        type_name = self._serialization_registry.type_name(message)
        
        # Register the serializer if not already registered
        if not self._serialization_registry.is_registered(type_name=type_name,
                                                          data_content_type=JSON_DATA_CONTENT_TYPE):
            self._serialization_registry.add_serializer(try_get_known_serializers_for_type(message))

        # Serialize the message to JSON format
        serialized = self._serialization_registry.serialize(message=message,
                                                            type_name=type_name,
                                                            data_content_type=JSON_DATA_CONTENT_TYPE)

        # Create a future to await the response from the Kafka topic
        future = asyncio.get_event_loop().create_future()
        
        # Generate a unique request ID for correlating request/response
        request_id = await self._get_new_request_id()
        
        # Store the future for response correlation
        self._pending_requests[request_id] = future

        # Create an AgentEvent with the serialized message
        event = AgentEvent(id=request_id, message=serialized, message_type=type_name)

        # Send the event to the Kafka topic asynchronously
        self._background_task_manager.add_task(
            StreamingWorkerBase.send_message(self,
                                             topic=self._config.request_topic,
                                             message=event,
                                             recipient=ctx.sender.__str__(),
                                             serializer=self._serializer)
        )
        
        # Return the future that will be resolved when response is received
        return await future

    async def save_state(self) -> Mapping[str, Any]:
        """Save the current state of the agent.
        
        Captures the agent's current state for persistence, checkpointing,
        or migration scenarios. The saved state can be later restored using
        load_state() to maintain continuity across agent restarts.
        
        Returns:
            A mapping containing the agent's state including:
            - next_request_id: The current request ID counter to avoid ID collisions after restart
        """
        # Use lock to ensure consistent state capture
        async with self._pending_requests_lock:
            return {
                "next_request_id": self._next_request_id
            }

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load a previously saved state into the agent.
        
        Restores the agent's state from a previously saved state mapping.
        This is useful for agent recovery, migration, or resuming from
        checkpoints. The method ensures that request ID generation continues
        safely without collisions.
        
        Args:
            state: A mapping containing the agent's state, typically from save_state()
                  Expected keys:
                  - next_request_id: The request ID counter to restore
        """
        # Use lock to ensure thread-safe state restoration
        async with self._pending_requests_lock:
            # Restore the request ID counter, ensuring it's at least as high as the saved value
            # to avoid ID collisions
            saved_request_id = state.get("next_request_id", 0)
            self._next_request_id = max(self._next_request_id, saved_request_id)
            
            # Note: We don't restore _pending_requests as those are runtime Future objects
            # that cannot be meaningfully serialized. They will be rebuilt as new requests come in.

    async def close(self) -> None:
        """Close the agent and release all resources.
        
        Performs cleanup operations including waiting for all background tasks
        to complete and releasing any held resources. This should be called
        when the agent is being shut down.
        """
        logging.info("Closing KafkaStreamingAgent and releasing resources.")
        
        # Cancel all pending requests with appropriate error
        async with self._pending_requests_lock:
            for request_id, future in self._pending_requests.items():
                if not future.done():
                    future.set_exception(
                        asyncio.CancelledError("Agent is being closed")
                    )
            self._pending_requests.clear()
        
        # Wait for all background tasks to complete before closing
        await self._background_task_manager.wait_for_completion()

    async def _get_new_request_id(self) -> str:
        """Generate a new unique request ID for correlating requests and responses.
        
        Creates a thread-safe, monotonically increasing request ID that can be
        used to correlate request and response messages in the Kafka messaging system.
        The ID is guaranteed to be unique within this agent instance.

        Returns:
            A unique string identifier for the request
        """
        # Use lock to ensure thread-safe ID generation
        async with self._pending_requests_lock:
            self._next_request_id += 1
            return str(self._next_request_id)

    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
        """Handle incoming Kafka events and resolve corresponding request futures.
        
        This method is called when a Kafka record is received from the subscribed topic.
        It processes AgentEvent messages, extracts the response data, and resolves
        the corresponding pending request Future.
        
        Args:
            record: The Kafka ConsumerRecord containing the event data
            stream: The Kafka stream instance for stream processing operations
            send: The send function for producing messages back to Kafka topics
        """
        # Validate that the record contains a value
        if record.value is None:
            logging.error("Received None value in KafkaStreamingAgent event")
            return
            
        # Ensure the record value is an AgentEvent
        if not isinstance(record.value, AgentEvent):
            logging.error(f"Received invalid message type: {type(record.value)}")
            return

        # Extract the AgentEvent from the record
        event: AgentEvent = record.value
        request_id = event.id
        
        # Check if we have a pending request for this ID
        if request_id not in self._pending_requests:
            logging.error(f"Received response for unknown request ID: {request_id}")
            return

        # Retrieve and remove the future from pending requests
        future = self._pending_requests.pop(request_id, None)
        if future is None:
            logging.error(f"Future for request ID {request_id} not found")
            return

        try:
            # Deserialize the response message from JSON
            # For now, we support only JSON serialization
            message: Dict[str, Any] = json.loads(event.message)
            
            # Resolve the future with the deserialized message
            future.set_result(message)
        except Exception as e:
            # If deserialization fails, resolve the future with the exception
            logging.error(f"Error deserializing message for request ID {request_id}: {e}")
            future.set_exception(e)
            return

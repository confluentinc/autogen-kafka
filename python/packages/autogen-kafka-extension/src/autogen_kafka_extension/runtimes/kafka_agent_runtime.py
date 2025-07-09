import asyncio
import logging
import uuid
from asyncio import Future
from typing import Dict, Callable, Awaitable, TypeVar, Any, Sequence, Mapping, Type

from autogen_core import (
    AgentRuntime, Agent, AgentId, Subscription, TopicId, CancellationToken,
    AgentType, AgentMetadata, MessageSerializer,
)
from kstreams import ConsumerRecord, Stream, Send
from opentelemetry.trace import TracerProvider

from autogen_kafka_extension import KafkaAgentRuntimeConfig
from autogen_kafka_extension.runtimes.messaging_client import MessagingClient
from autogen_kafka_extension.runtimes.services.agent_registry import AgentRegistry
from autogen_kafka_extension.runtimes.services.agent_manager import AgentManager
from autogen_kafka_extension.runtimes.services.cloud_event_processor import CloudEventProcessor
from autogen_kafka_extension.shared.events.request_event import RequestEvent
from autogen_kafka_extension.shared.streaming_worker_base import StreamingWorkerBase
from autogen_kafka_extension.runtimes.services.message_processor import MessageProcessor
from autogen_kafka_extension.runtimes.services.subscription_service import SubscriptionService

T = TypeVar("T", bound=Agent)
logger = logging.getLogger(__name__)

class KafkaAgentRuntime(StreamingWorkerBase[KafkaAgentRuntimeConfig], AgentRuntime):
    """
    A Kafka-based agent runtime for distributed multi-agent systems.
    
    This class provides a complete implementation of the AgentRuntime interface using
    Apache Kafka as the underlying messaging infrastructure. It enables distributed
    agent communication across multiple processes and machines through Kafka topics.
    
    Architecture:
        The runtime is built on several key components:
        - AgentRegistry: Manages agent discovery and registration across the cluster
        - SubscriptionService: Handles topic subscriptions and message routing
        - MessagingClient: Provides high-level messaging APIs for agents
        - MessageProcessor: Processes incoming messages and routes them to agents
        - AgentManager: Manages local agent instances and their lifecycle
        
    Features:
        - Distributed agent communication via Kafka
        - Automatic agent discovery and registration
        - Topic-based publish/subscribe messaging
        - Request/response messaging patterns
        - State persistence and recovery
        - OpenTelemetry integration for observability
        - Graceful shutdown and error handling
        
    Usage:
        ```python
        config = WorkerConfig(...)
        runtime = KafkaWorkerAgentRuntime(config)
        
        # Register agent factories
        await runtime.register_factory("my_agent_type", MyAgent)
        
        # Start the runtime
        await runtime.start()
        
        # Runtime will process messages until stopped
        await runtime.stop()
        ```
        
    Thread Safety:
        This class is designed to be used from a single asyncio event loop.
        All public methods are async and should be awaited from the same loop.
        
    Attributes:
        _agent_registry: Registry for agent discovery and management
        _subscription_svc: Service for managing message subscriptions
        _messaging_client: Client for sending and receiving messages
        _agent_manager: Manager for local agent instances
        _message_processor: Processor for incoming messages
        _pending_requests: Cache for pending request/response operations
    """

    def __init__(
        self,
        config: KafkaAgentRuntimeConfig,
        tracer_provider: TracerProvider | None = None
    ) -> None:
        """Initialize a new KafkaAgentRuntime instance.
        
        Sets up the Kafka worker runtime with all necessary components including
        agent registry, subscription service, messaging client, and message processor.
        This constructor initializes all components but does not start any background
        services - call start() to begin message processing.
        
        Args:
            config: Worker configuration containing Kafka settings, topics, and other
                   runtime parameters. Must include valid Kafka broker information,
                   consumer group settings, and topic configurations.
            tracer_provider: Optional OpenTelemetry tracer provider for distributed
                           tracing. If None, no tracing will be configured. When provided,
                           enables detailed observability across the distributed system.
                           
        Raises:
            ValueError: If the configuration is invalid or missing required fields.
            ConnectionError: If initial Kafka connection validation fails.
        """
        AgentRuntime.__init__(self)
        StreamingWorkerBase.__init__(self,
                                     config = config,
                                     topic=config.request_topic,
                                     monitoring=tracer_provider,
                                     target_type=RequestEvent)

        # Kafka components
        self._agent_registry : AgentRegistry = AgentRegistry(config=config,
                                                             streaming_service=self._service_manager.service,
                                                             monitoring=self._trace_helper)
        self._subscription_svc: SubscriptionService = SubscriptionService(config=self._config,
                                                                          streaming_service=self._service_manager.service,
                                                                          monitoring=self._trace_helper)
        self._messaging_client : MessagingClient = MessagingClient(config=self._config,
                                                                   streaming_service=self._service_manager.service,
                                                                   serialization_registry=self._serialization_registry,
                                                                   monitoring=self._trace_helper)

        # Component managers
        self._agent_manager = AgentManager(self)
        self._message_processor = MessageProcessor(
            self._agent_manager,
            self._serialization_registry,
            self._subscription_svc,
            self._trace_helper,
            self._config
        )

        # Cloud event processor for handling CloudEvents
        self._cloud_event_processor : CloudEventProcessor = CloudEventProcessor(config=self._config,
                                                                                message_processor=self._message_processor)

        # Request/response handling
        self._pending_requests: Dict[str, Future[Any]] = {}
        self._pending_requests_lock = asyncio.Lock()

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

    async def start(self, ) -> None:
        """Start the Kafka stream processing engine and subscribe to topics.
        
        Initializes and starts all internal services in the correct order:
        1. Subscription service for managing agent subscriptions
        2. Messaging client for sending/receiving messages
        3. Agent registry for agent discovery and management
        4. Underlying streaming service for Kafka connectivity
        
        This method is idempotent - calling it multiple times has no additional effect.
        """
        if self.is_started:
            return

        logger.info("Starting runtime...")

        # Start all services
        await self._subscription_svc.start()
        await self._messaging_client.start()
        await self._agent_registry.start()
        await self._cloud_event_processor.start()

        # Start the streaming service
        await super().start()

    async def stop(self) -> None:
        """Stop the Kafka stream processing engine and wait for background tasks to finish.
        
        Gracefully shuts down all services in reverse order of startup:
        1. Unsubscribes from all topics
        2. Stops messaging client
        3. Stops agent registry
        4. Stops subscription service
        5. Stops underlying streaming service
        
        This method is idempotent - calling it multiple times has no additional effect.
        """
        if not self.is_started:
            return

        logger.info("Stopping subscription service and Kafka stream engine...")
        await self._subscription_svc.unsubscribe_all()


        # Stop all services
        await self._messaging_client.stop()
        await self._agent_registry.stop()
        await self._subscription_svc.stop()
        await self._cloud_event_processor.stop()

        await super().stop()

    async def send_message(
        self,
        message: Any,
        recipient: AgentId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None
    ) -> Any:
        """Send a message to a specific agent.
        
        Routes a message to the specified recipient agent through the messaging client.
        The message will be serialized and sent via Kafka to the appropriate topic.
        
        Args:
            message: The message payload to send. Can be any serializable object.
            recipient: The AgentId of the agent that should receive the message.
            sender: Optional AgentId of the sending agent. If None, the message
                   will be sent without sender identification.
            cancellation_token: Optional token for cancelling the operation.
                              Currently not implemented in the messaging client.
            message_id: Optional unique identifier for the message. If None,
                       a new ID will be generated automatically.
                       
        Returns:
            The response from the messaging client, typically indicating
            successful message delivery.
        """
        return await self._messaging_client.send_message(
            message=message,
            recipient=recipient,
            sender=sender,
            message_id=message_id
        )

    async def publish_message(
        self,
        message: Any,
        topic_id: TopicId,
        *,
        sender: AgentId | None = None,
        cancellation_token: CancellationToken | None = None,
        message_id: str | None = None,
    ) -> None:
        """Publish a message to a specific topic.
        
        Broadcasts a message to all subscribers of the specified topic through
        the messaging client. The message will be serialized and published via Kafka.
        
        Args:
            message: The message payload to publish. Can be any serializable object.
            topic_id: The TopicId identifying which topic to publish to.
            sender: Optional AgentId of the publishing agent. If None, the message
                   will be published without sender identification.
            cancellation_token: Optional token for cancelling the operation.
                              Currently not implemented in the messaging client.
            message_id: Optional unique identifier for the message. If None,
                       a new ID will be generated automatically.
        """
        await self._messaging_client.publish_message(
            message=message,
            topic_id=topic_id,
            sender=sender,
            message_id=message_id
        )

    async def remove_subscription(self, id: str) -> None:
        """Remove a subscription by its ID.
        
        Unsubscribes from the specified subscription, stopping message delivery
        for that subscription. The agent will no longer receive messages matching
        the subscription criteria.
        
        Args:
            id: The unique identifier of the subscription to remove.
        """
        await self._subscription_svc.remove_subscription(id)

    async def add_subscription(self, subscription: Subscription) -> None:
        """Add a new subscription.
        
        Registers a new subscription with the subscription service, enabling
        the agent to receive messages that match the subscription criteria.
        
        Args:
            subscription: The Subscription object defining the subscription
                         parameters, including topic filters, agent ID, and
                         message type filters.
        """
        await self._subscription_svc.add_subscription(subscription)

    async def register_factory(
        self,
        type: str | AgentType,
        agent_factory: Callable[[], T | Awaitable[T]],
        *,
        expected_class: type[T] | None = None
    ) -> AgentType:
        """Register a factory for creating agents of a given type.
        
        Registers a factory function that can create agent instances of the specified
        type. The factory will be called when new agents of this type need to be
        instantiated.
        
        Args:
            type: The agent type identifier, either as a string or AgentType object.
            agent_factory: A callable that returns an agent instance, either
                          synchronously or asynchronously.
            expected_class: Optional type constraint for type checking. The factory
                           must produce instances of this class.
                           
        Returns:
            The AgentType object representing the registered agent type.
        """
        return await self._agent_manager.register_factory(
            type, agent_factory, self._agent_registry, expected_class=expected_class
        )

    async def register_agent_instance(
        self,
        agent_instance: Agent,
        agent_id: AgentId,
    ) -> AgentId:
        """Register a specific agent instance with a given ID.
        
        Registers an already-instantiated agent with the specified ID, making it
        available for message processing and subscription handling.
        
        Args:
            agent_instance: The Agent instance to register.
            agent_id: The unique AgentId to assign to this agent instance.
            
        Returns:
            The AgentId that was assigned to the registered agent.
        """
        return await self._agent_manager.register_instance(agent_instance, agent_id)

    async def save_state(self) -> Mapping[str, Any]:
        """Save the state of all registered agents.
        
        Collects and serializes the state from all currently registered agent
        instances, returning a mapping that can be used to restore the runtime
        state later. This is useful for implementing checkpointing, migration,
        or disaster recovery scenarios.
        
        The returned state includes:
        - agent_states: A mapping of agent IDs to their serialized states
        - Additional runtime metadata (future extension point)
        
        Returns:
            A mapping containing the serialized state of all agents, organized
            by agent ID under the "agent_states" key. The structure is:
            {
                "agent_states": {
                    "agent_id_1": {...state_data...},
                    "agent_id_2": {...state_data...},
                    ...
                }
            }
            
        Raises:
            ValueError: If any agent instance is not found or cannot be accessed.
            RuntimeError: If state serialization fails for any agent.
        """
        all_states = {
            "agent_states": {}
        }
        for agent_id, agent_instance in self._agent_manager.agents:
            if agent_instance is None:
                raise ValueError(f"Agent with ID {agent_id} not found.")
            state = await agent_instance.save_state()
            metadata = await agent_instance.save_metadata()
            all_states["agent_states"][agent_id] = state

        return all_states

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load previously saved state into all registered agents.
        
        Restores the state of all agents from a previously saved state mapping.
        The agents must already be registered before loading their state.
        This method validates the state format and ensures all referenced
        agents exist before attempting to load any state.
        
        Args:
            state: A mapping containing the serialized agent states, typically
                  created by a previous call to save_state(). Must contain
                  an "agent_states" key with a mapping of agent IDs to state data.
                  Expected structure:
                  {
                      "agent_states": {
                          "agent_id_1": {...state_data...},
                          "agent_id_2": {...state_data...},
                          ...
                      }
                  }
                  
        Raises:
            ValueError: If the state format is invalid, missing required keys,
                       or if any referenced agent is not found.
            RuntimeError: If state loading fails for any agent.
        """
        if "agent_states" not in state:
            raise ValueError("State must contain 'agent_states' key.")

        for agent_id, agent_state in state["agent_states"].items():
            agent_instance: Agent = await self._agent_manager.get_agent(agent_id)
            if agent_instance is None:
                raise ValueError(f"Agent with ID {agent_id} not found.")
            await agent_instance.load_state(agent_state)

    async def agent_metadata(self, agent: AgentId) -> AgentMetadata:
        """Get metadata for a specific agent.
        
        Retrieves the metadata associated with the specified agent, including
        information about the agent's type, capabilities, and configuration.
        
        Args:
            agent: The AgentId of the agent whose metadata to retrieve.
            
        Returns:
            The AgentMetadata object containing the agent's metadata.
            
        Raises:
            ValueError: If the specified agent is not found.
        """
        agent_instance: Agent = await self._agent_manager.get_agent(agent)
        if agent_instance is None:
            raise ValueError(f"Agent with ID {agent} not found.")

        return agent_instance.metadata

    async def agent_save_state(self, agent: AgentId) -> Mapping[str, Any]:
        """Save the state of a specific agent.
        
        Serializes and returns the current state of the specified agent instance.
        
        Args:
            agent: The AgentId of the agent whose state to save.
            
        Returns:
            A mapping containing the serialized state of the agent.
            
        Raises:
            ValueError: If the specified agent is not found.
        """
        agent_instance: Agent = await self._agent_manager.get_agent(agent)
        if agent_instance is None:
            raise ValueError(f"Agent with ID {agent} not found.")

        return await agent_instance.save_state()

    async def agent_load_state(self, agent: AgentId, state: Mapping[str, Any]) -> None:
        """Load state into a specific agent.
        
        Restores the state of the specified agent from the provided state mapping.
        
        Args:
            agent: The AgentId of the agent whose state to load.
            state: A mapping containing the serialized agent state.
            
        Raises:
            ValueError: If the specified agent is not found.
        """
        agent_instance: Agent = await self._agent_manager.get_agent(agent)
        if agent_instance is None:
            raise ValueError(f"Agent with ID {agent} not found.")

        await agent_instance.load_state(state)

    async def try_get_underlying_agent_instance(self, id: AgentId, type: Type[T] = Agent) -> T:  # type: ignore[assignment]
        """Get the underlying agent instance with type checking.
        
        Retrieves the actual agent instance for the specified AgentId, with
        optional type checking to ensure the agent is of the expected type.
        
        Args:
            id: The AgentId of the agent instance to retrieve.
            type: The expected type of the agent instance. Defaults to Agent.
            
        Returns:
            The underlying agent instance, cast to the specified type.
            
        Raises:
            ValueError: If the agent is not found.
            TypeError: If the agent is not of the expected type.
        """
        return await self._agent_manager.try_get_underlying_agent_instance(id, type)

    async def _get_new_request_id(self) -> str:
        """Generate a new unique request ID for correlating requests and responses.
        
        Creates a thread-safe, monotonically increasing request ID that can be
        used to correlate request and response messages in the messaging system.
        
        Returns:
            A unique string identifier for the request.
        """
        async with self._pending_requests_lock:
            return uuid.uuid4().hex

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
        self._background_task_manager.add_task(
            self._message_processor.process_request(cr.value, send)
        )

    def add_message_serializer(self, serializer: MessageSerializer[Any] | Sequence[MessageSerializer[Any]]) -> None:
        """Add one or more message serializers to the runtime.
        
        Registers message serializers with the serialization registry, enabling
        the runtime to serialize and deserialize custom message types for
        Kafka transport.
        
        Args:
            serializer: A single MessageSerializer or a sequence of MessageSerializers
                       to register. Each serializer defines how to convert between
                       Python objects and their serialized representation.
        """
        self._serialization_registry.add_serializer(serializer)
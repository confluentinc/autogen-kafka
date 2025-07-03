import logging
from typing import Dict, Union, Optional

from autogen_core import AgentType
from autogen_core._serialization import SerializationRegistry
from autogen_core._telemetry import TraceHelper
from kstreams import ConsumerRecord, Stream, Send
from opentelemetry.trace import TracerProvider

from ...config.agent_runtime_config import KafkaAgentRuntimeConfig
from ...shared.events.events_serdes import EventSerializer
from ...shared.events.registration_event import RegistrationEvent, RegistrationMessageType
from ...shared.streaming_service import StreamingService
from ...shared.streaming_worker_base import StreamingWorkerBase

logger = logging.getLogger(__name__)


class AgentRegistry(StreamingWorkerBase[KafkaAgentRuntimeConfig]):
    """
    A registry for agents that can be used to manage and retrieve agents.
    
    This class provides distributed agent registration via Kafka streams,
    allowing multiple workers to coordinate agent availability.
    """

    def __init__(self,
                 config: KafkaAgentRuntimeConfig,
                 streaming_service: StreamingService | None = None,
                 monitoring: TraceHelper | TracerProvider | None = None,
                 serialization_registry: SerializationRegistry = SerializationRegistry()) -> None:
        """
        Initialize the AgentRegistry.
        
        This constructor sets up a distributed agent registry that uses Kafka streams
        for coordinating agent availability across multiple workers.
        
        Args:
            config (KafkaAgentRuntimeConfig): Configuration object containing registry settings
                including the registry topic name and other worker configuration.
            streaming_service (Optional[StreamingService], optional): Service for handling
                Kafka streaming operations. If None, a default service will be created.
                Defaults to None.
            monitoring (TraceHelper | TracerProvider | None, optional): Helper for distributed tracing
                and telemetry collection. Defaults to None.
            serialization_registry (SerializationRegistry, optional): Registry for message
                serialization/deserialization. Defaults to a new SerializationRegistry instance.
        
        Raises:
            Exception: If the configuration is invalid or streaming service initialization fails.
        """
        super().__init__(config = config,
                         topic=config.registry_topic,
                         monitoring=monitoring,
                         streaming_service=streaming_service,
                         serialization_registry=serialization_registry,
                         target_type=RegistrationEvent)

        self._agents: Dict[str, Union[str, AgentType]] = {}
        self._serializer = EventSerializer(
            topic=config.registry_topic,
            source_type=RegistrationEvent,
            kafka_utils=self._kafka_config.utils()
        )

    def _extract_agent_key(self, agent: Union[str, AgentType]) -> str:
        """
        Extract the string key from an agent identifier.
        
        This method normalizes agent identifiers to string keys for consistent
        storage and lookup in the registry. It handles both string identifiers
        and AgentType objects.
        
        Args:
            agent (Union[str, AgentType]): The agent identifier, either a string
                key or an AgentType object containing type information.
        
        Returns:
            str: The string key representing the agent. For AgentType objects,
                returns the 'type' attribute; for strings, returns the string itself.
        """
        return agent.type if isinstance(agent, AgentType) else agent

    async def register_agent(self, agent: Union[str, AgentType]) -> None:
        """
        Register an agent with the registry.
        
        Args:
            agent: The agent to register (either a string identifier or AgentType)
            
        Raises:
            Exception: If the registration fails
        """
        key = self._extract_agent_key(agent)
        
        # Store the agent locally first
        self._agents[key] = agent
        logger.info(f"Registering agent locally: {key}")

        try:
            # Broadcast registration to other workers
            await self._send_registration_message(
                message_type=RegistrationMessageType.REGISTER,
                agent_key=key
            )
            logger.info(f"Successfully registered agent: {key}")
        except Exception as e:
            # Rollback local registration on failure
            self._agents.pop(key, None)
            logger.error(f"Failed to register agent {key}: {e}")
            raise

    async def unregister_agent(self, agent: Union[str, AgentType]) -> None:
        """
        Unregister an agent from the registry.
        
        Args:
            agent: The agent to unregister (either a string identifier or AgentType)
        """
        key = self._extract_agent_key(agent)
        
        if key not in self._agents:
            logger.warning(f"Attempted to unregister non-registered agent: {key}")
            return

        # Remove locally first
        del self._agents[key]
        logger.info(f"Unregistering agent locally: {key}")

        try:
            # Broadcast unregistration to other workers
            await self._send_registration_message(
                message_type=RegistrationMessageType.UNREGISTER,
                agent_key=key
            )
            logger.info(f"Successfully unregistered agent: {key}")
        except Exception as e:
            logger.error(f"Failed to broadcast unregistration for agent {key}: {e}")
            # Note: We don't rollback local unregistration as it's safer to have
            # the agent removed locally even if broadcast fails

    def is_registered(self, agent: Union[str, AgentType]) -> bool:
        """
        Check if an agent is registered.
        
        Args:
            agent: The agent to check (either a string identifier or AgentType)
            
        Returns:
            True if the agent is registered, False otherwise
        """
        key = self._extract_agent_key(agent)
        return key in self._agents

    def get_registered_agents(self) -> Dict[str, Union[str, AgentType]]:
        """
        Get a copy of all registered agents.
        
        Returns:
            A dictionary mapping agent keys to agent objects
        """
        return self._agents.copy()

    async def _send_registration_message(
        self, 
        message_type: RegistrationMessageType, 
        agent_key: str
    ) -> None:
        """
        Send a registration message to the Kafka topic.
        
        Args:
            message_type: The type of registration message
            agent_key: The key of the agent
        """
        message = RegistrationEvent(message_type=message_type, agent=agent_key)
        
        await self.send_message(
            topic=self._config.registry_topic,
            message=message,
            recipient=agent_key,
            serializer=self._serializer
        )

    async def _handle_event(self, record: ConsumerRecord, stream: Stream, send: Send) -> None:
        """
        Handle incoming registration messages from other workers.
        
        Args:
            record: The consumer record containing the registration message
            stream: The Kafka stream
            send: The send function for producing messages
        """
        if not isinstance(record.value, RegistrationEvent):
            logger.error(f"Received invalid message type: {type(record.value)}")
            return

        message = record.value
        agent_key = message.agent

        try:
            if message.message_type == RegistrationMessageType.REGISTER:
                self._handle_remote_registration(agent_key)
            elif message.message_type == RegistrationMessageType.UNREGISTER:
                self._handle_remote_unregistration(agent_key)
            else:
                logger.error(f"Unknown registration message type: {message.message_type}")
        except Exception as e:
            logger.error(f"Error processing registration message for agent {agent_key}: {e}")

    def _handle_remote_registration(self, agent_key: str) -> None:
        """
        Handle registration message from another worker.
        
        Args:
            agent_key: The key of the agent being registered
        """
        if agent_key in self._agents:
            logger.debug(f"Agent {agent_key} is already registered locally")
        else:
            # For remote registrations, we only store the key since we don't have
            # access to the actual agent object
            self._agents[agent_key] = agent_key
            logger.info(f"Registered remote agent: {agent_key}")

    def _handle_remote_unregistration(self, agent_key: str) -> None:
        """
        Handle unregistration message from another worker.
        
        Args:
            agent_key: The key of the agent being unregistered
        """
        if agent_key in self._agents:
            del self._agents[agent_key]
            logger.info(f"Unregistered remote agent: {agent_key}")
        else:
            logger.debug(f"Attempted to unregister non-registered remote agent: {agent_key}")

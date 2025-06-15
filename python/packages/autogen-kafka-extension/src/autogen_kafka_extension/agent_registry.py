import logging
from typing import Dict, Union

from autogen_core import AgentType
from kstreams import ConsumerRecord, Stream, Send

from autogen_kafka_extension.events.message_serdes import EventSerializer
from autogen_kafka_extension.events.registration import RegistrationMessage, RegistrationMessageType
from autogen_kafka_extension.streaming_service import StreamingService
from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    A registry for agents that can be used to manage and retrieve agents.
    
    This class provides distributed agent registration via Kafka streams,
    allowing multiple workers to coordinate agent availability.
    """

    def __init__(self, config: WorkerConfig, streaming: StreamingService | None = None) -> None:
        self._agents: Dict[str, Union[str, AgentType]] = {}
        self._started: bool = False
        self._config = config
        self._streaming = streaming if streaming else StreamingService(config)
        
        # Set up the registration stream
        self._setup_registration_stream()

    def _setup_registration_stream(self) -> None:
        """Set up the Kafka stream for agent registration messages."""
        self._streaming.create_and_add_stream(
            name=f"{self._config.title}_reg",
            topics=[self._config.registry_topic],
            group_id=f"{self._config.group_id}_reg",
            client_id=f"{self._config.client_id}_reg",
            func=self._on_record
        )

    def _extract_agent_key(self, agent: Union[str, AgentType]) -> str:
        """Extract the string key from an agent identifier."""
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
        message = RegistrationMessage(message_type=message_type, agent=agent_key)
        
        await self._streaming.send(
            topic=self._config.registry_topic,
            value=message,
            key=agent_key,
            headers={},
            serializer=EventSerializer()
        )

    async def _on_record(self, cr: ConsumerRecord, stream: Stream, send: Send) -> None:
        """
        Handle incoming registration messages from other workers.
        
        Args:
            cr: The consumer record containing the registration message
            stream: The Kafka stream
            send: The send function for producing messages
        """
        if not isinstance(cr.value, RegistrationMessage):
            logger.error(f"Received invalid message type: {type(cr.value)}")
            return

        message = cr.value
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

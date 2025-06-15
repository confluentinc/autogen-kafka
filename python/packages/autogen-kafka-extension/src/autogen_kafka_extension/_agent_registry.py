import logging

from autogen_core import AgentType
from kstreams import ConsumerRecord, Stream, Send

from autogen_kafka_extension.events._message_serdes import EventSerializer
from autogen_kafka_extension.events._registration import RegistrationMessage, RegistrationMessageType
from autogen_kafka_extension._streaming import Streaming
from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)

class AgentRegistry:
    """
    A registry for agents that can be used to manage and retrieve agents.
    """

    def __init__(self, config: WorkerConfig,
                 streaming: Streaming | None = None) -> None:
        self._agents = {}
        self._started: bool = False
        self._config = config
        self._streaming = streaming if streaming else Streaming(config)
        self._streaming.create_and_add_stream(
            name=config.title + "_reg",
            topics=[self._config.registry_topic],
            group_id=self._config.group_id + "_reg",
            client_id=self._config.client_id + "_reg",
            func=self._on_record
        )

    async def register_agent(self, agent : str | AgentType):
        """
        Register an agent with a given name.
        """
        key: str = agent.type if isinstance(agent, AgentType) else agent
        self._agents[key] = agent
        try:
            await self._streaming.send(
                topic=self._config.registry_topic,
                value=RegistrationMessage(message_type=RegistrationMessageType.REGISTER, agent=key),
                key=key,
                headers={},
                serializer=EventSerializer()
            )
        except Exception as e:
            logger.error(f"Failed to register agent {key}: {e}")
            raise

    def is_registered(self, agent: str | AgentType) -> bool:
        """
        Check if an agent is registered.
        """
        key: str = agent.type if isinstance(agent, AgentType) else agent
        return key in self._agents

    async def unregister_agent(self, agent: str | AgentType):
        """
        Unregister an agent with a given name.
        """
        key: str = agent.type if isinstance(agent, AgentType) else agent
        if key in self._agents:
            del self._agents[key]
            await self._streaming.send(
                topic=self._config.registry_topic,
                value=RegistrationMessage(message_type=RegistrationMessageType.UNREGISTER, agent=key),
                key=key,
                serializer=EventSerializer()
            )
        else:
            logger.warning(f"Attempted to unregister non-registered agent: {agent}")

    async def _on_record(self, cr: ConsumerRecord, stream: Stream, send: Send) -> None:
        if not isinstance(cr.value, RegistrationMessage):
            logger.error(f"Failed to send message to Kafka: {cr.value}")
            return

        if cr.value.message_type == RegistrationMessageType.REGISTER:
            if cr.value.agent in self._agents:
                logger.debug(f"Agent {cr.value.agent} is already registered.")
            else:
                logger.info(f"Registering agent: {cr.value.agent}")
                self._agents[cr.value.agent] = cr.value.agent
        elif cr.value.message_type == RegistrationMessageType.UNREGISTER:
            if cr.value.agent in self._agents:
                del self._agents[cr.value.agent]
            else:
                logger.warning(f"Attempted to unregister non-registered agent: {cr.value.agent}")
        else:
            logger.error(f"Unknown registration message type: {cr.value.message_type}")

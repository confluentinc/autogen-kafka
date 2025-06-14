import logging

from autogen_core import AgentType
from kstreams import create_engine, StreamEngine, middleware, ConsumerRecord, Stream, Send
from kstreams.backends import Kafka

from autogen_kafka_extension._message_serdes import EventSerializer, EventDeserializer
from autogen_kafka_extension._registration import RegistrationMessage, RegistrationMessageType
from autogen_kafka_extension._topic_admin import TopicAdmin
from autogen_kafka_extension.worker_config import WorkerConfig

logger = logging.getLogger(__name__)

class AgentRegistry:
    """
    A registry for agents that can be used to manage and retrieve agents.
    """

    def __init__(self,
                 config: WorkerConfig):
        self._agents = {}
        self._started: bool = False
        self._config = config
        self._stream_engine: StreamEngine | None = None

    def start(self,
              stream_engine: StreamEngine | None = None) -> None:
        try:
            self._stream_engine = stream_engine

            # Make sure all topics exist
            topics_admin = TopicAdmin(self._config)
            topics_admin.create_topics(topics=[self._config.registry_topic])

            # Create and add a stream for incoming requests
            stream = Stream(
                topics=[self._config.registry_topic],
                name=self._config.title + "_reg",
                func=self._on_record,
                middlewares=[middleware.Middleware(EventDeserializer)],
                config={
                    "group_id": self._config.group_id + "_reg",
                    "client_id": self._config.client_id + "_reg",
                    "auto_offset_reset": "latest",
                    "enable_auto_commit": True
                },
            )

            self._stream_engine.add_stream(stream)
        except Exception as e:
            logger.error(f"Failed to start AgentRegistry: {e}")
            raise RuntimeError(f"Failed to start AgentRegistry: {e}") from e

    async def register_agent(self, agent : str | AgentType):
        """
        Register an agent with a given name.
        """
        key: str = agent.type if isinstance(agent, AgentType) else agent
        self._agents[key] = agent
        await self._stream_engine.send(
            topic=self._config.registry_topic,
            value=RegistrationMessage(message_type=RegistrationMessageType.REGISTER, agent=key),
            key=key,
            headers={},
            serializer=EventSerializer()
        )

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
            await self._stream_engine.send(
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
            self._agents[cr.value.agent] = cr.value.agent
        elif cr.value.message_type == RegistrationMessageType.UNREGISTER:
            if cr.value.agent in self._agents:
                del self._agents[cr.value.agent]
            else:
                logger.warning(f"Attempted to unregister non-registered agent: {cr.value.agent}")
        else:
            logger.error(f"Unknown registration message type: {cr.value.message_type}")

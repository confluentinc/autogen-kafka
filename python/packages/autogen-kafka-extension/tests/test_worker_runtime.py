import asyncio
import pytest
from autogen_core import try_get_known_serializers_for_type, AgentType, AgentId, TopicId, TypeSubscription
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism
from testcontainers.kafka import KafkaContainer

from autogen_kafka_extension.worker_config import WorkerConfig
from autogen_kafka_extension.worker_runtime import KafkaWorkerAgentRuntime
from utils import LoopbackAgent, MessageType, NoopAgent


@pytest.mark.asyncio
async def test_agent_types_must_be_unique_single_worker() -> None:
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()

        config_1: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              response_topic="response",
                                              registry_topic="communication",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_1",
                                              client_id="autogen-client_1")

        worker = KafkaWorkerAgentRuntime(config=config_1)
        await worker.start()

        await worker.register_factory(type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

        with pytest.raises(ValueError):
            await worker.register_factory(
                type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent
            )

        await worker.register_factory(type=AgentType("name4"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)
        await worker.register_factory(type=AgentType("name5"), agent_factory=lambda: NoopAgent())

        await worker.stop()

@pytest.mark.asyncio
async def test_agent_types_must_be_unique_multiple_workers() -> None:
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()

        config_1: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              response_topic="response",
                                              registry_topic="registry",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_1",
                                              client_id="autogen-client_1")
        config_2: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              response_topic="response",
                                              registry_topic="registry",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_2",
                                              client_id="autogen-client_2")

        worker1 = KafkaWorkerAgentRuntime(config=config_1)
        await worker1.start()

        worker2 = KafkaWorkerAgentRuntime(config=config_2)
        await worker2.start()

        await worker1.register_factory(type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

        await asyncio.sleep(10)

        with pytest.raises(Exception, match="Agent type name1 already registered"):
            await worker2.register_factory(
                type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent
            )

        await worker2.register_factory(type=AgentType("name4"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

        await worker1.stop()
        await worker2.stop()

@pytest.mark.asyncio
async def test_register_receives_publish() -> None:
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()

        config_1: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              response_topic="response",
                                              registry_topic="communication",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_1",
                                              client_id="autogen-client_1")
        config_2: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              response_topic="response",
                                              registry_topic="communication",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_2",
                                              client_id="autogen-client_2")

        worker1 = KafkaWorkerAgentRuntime(config=config_1)
        await worker1.start()

        worker1.add_message_serializer(try_get_known_serializers_for_type(MessageType))
        await worker1.register_factory(
            type=AgentType("name1"), agent_factory=lambda: LoopbackAgent(), expected_class=LoopbackAgent
        )
        await worker1.add_subscription(TypeSubscription("default", "name1"))

        worker2 = KafkaWorkerAgentRuntime(config=config_2)
        await worker2.start()
        worker2.add_message_serializer(try_get_known_serializers_for_type(MessageType))
        await worker2.register_factory(
            type=AgentType("name2"), agent_factory=lambda: LoopbackAgent(), expected_class=LoopbackAgent
        )
        await worker2.add_subscription(TypeSubscription("default", "name2"))

        # Publish message from worker1
        await worker1.publish_message(MessageType(), topic_id=TopicId("default", "default"))

        # Let the agent run for a bit.
        await asyncio.sleep(10)

        # Agents in default topic source should have received the message.
        worker1_agent = await worker1.try_get_underlying_agent_instance(AgentId("name1", "default"), LoopbackAgent)
        assert worker1_agent.num_calls == 1
        worker2_agent = await worker2.try_get_underlying_agent_instance(AgentId("name2", "default"), LoopbackAgent)
        assert worker2_agent.num_calls == 1

        # Agents in other topic source should not have received the message.
        worker1_agent = await worker1.try_get_underlying_agent_instance(AgentId("name1", "other"), LoopbackAgent)
        assert worker1_agent.num_calls == 0
        worker2_agent = await worker2.try_get_underlying_agent_instance(AgentId("name2", "other"), LoopbackAgent)
        assert worker2_agent.num_calls == 0

        await worker1.stop()
        await worker2.stop()
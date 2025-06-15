import asyncio
from typing import List

import pytest
from autogen_core import try_get_known_serializers_for_type, AgentType, AgentId, TopicId, TypeSubscription, \
    Subscription, DefaultTopicId
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism
from testcontainers.kafka import KafkaContainer

from autogen_kafka_extension.subscription_service import SubscriptionService
from autogen_kafka_extension.worker_config import WorkerConfig
from autogen_kafka_extension.worker_runtime import KafkaWorkerAgentRuntime
from utils import LoopbackAgent, MessageType, NoopAgent, CascadingAgent, ContentMessage, CascadingMessageType, \
    LoopbackAgentWithDefaultSubscription


@pytest.mark.asyncio
async def test_agent_types_must_be_unique_single_worker() -> None:
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()

        config_1: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              subscription_topic="subscription",
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
                                              subscription_topic="subscription",
                                              registry_topic="registry",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_1",
                                              client_id="autogen-client_1")
        config_2: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              subscription_topic="subscription",
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

        await asyncio.sleep(3)

        await worker1.register_factory(type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

        await asyncio.sleep(3)

        with pytest.raises(Exception, match="Agent type name1 already registered"):
            await worker2.register_factory(
                type=AgentType("name1"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent
            )

        await worker2.register_factory(type=AgentType("name4"), agent_factory=lambda: NoopAgent(), expected_class=NoopAgent)

        await worker1.stop()
        await worker2.stop()

@pytest.mark.asyncio
async def test_disconnected_agent() -> None:
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()

        config_1: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              subscription_topic="subscription",
                                              registry_topic="registry",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_1",
                                              client_id="autogen-client_1")
        config_2: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              subscription_topic="subscription",
                                              registry_topic="registry",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_2",
                                              client_id="autogen-client_2")

        subscriptions = SubscriptionService(config=config_1)
        await subscriptions.start()
        worker1 = KafkaWorkerAgentRuntime(config=config_1)
        worker1_2 = KafkaWorkerAgentRuntime(config=config_2)

        # TODO: Implementing `get_current_subscriptions` and `get_subscribed_recipients` requires access
        # to some private properties. This needs to be updated once they are available publicly

        def get_current_subscriptions() -> List[Subscription]:
            return subscriptions.get_all_subscriptions() # type: ignore[reportPrivateUsage]

        async def get_subscribed_recipients() -> List[AgentId]:
            return await subscriptions.get_all_subscribed_recipients(DefaultTopicId())  # type: ignore[reportPrivateUsage]

        try:
            await worker1.start()
            await asyncio.sleep(3)

            await LoopbackAgentWithDefaultSubscription.register(
                worker1, "worker1", lambda: LoopbackAgentWithDefaultSubscription()
            )

            await asyncio.sleep(3)

            subscriptions1 = get_current_subscriptions()
            assert len(subscriptions1) == 2
            recipients1 = await get_subscribed_recipients()
            assert AgentId(type="worker1", key="default") in recipients1

            first_subscription_id = subscriptions1[0].id

            await worker1.publish_message(ContentMessage(content="Hello!"), DefaultTopicId())
            # This is a simple simulation of worker disconnect
            if worker1.is_started is not None:  # type: ignore[reportPrivateUsage]
                try:
                    await worker1.stop()  # type: ignore[reportPrivateUsage]
                except asyncio.CancelledError:
                    pass

            await asyncio.sleep(1)

            await worker1_2.start()
            await asyncio.sleep(3)

            subscriptions2 = get_current_subscriptions()
            assert len(subscriptions2) == 0
            recipients2 = await get_subscribed_recipients()
            assert len(recipients2) == 0
            await asyncio.sleep(1)

            await LoopbackAgentWithDefaultSubscription.register(
                worker1_2, "worker1", lambda: LoopbackAgentWithDefaultSubscription()
            )

            await asyncio.sleep(3)

            subscriptions3 = get_current_subscriptions()
            assert len(subscriptions3) == 2
            assert first_subscription_id not in [x.id for x in subscriptions3]

            recipients3 = await get_subscribed_recipients()
            assert len(set(recipients2)) == len(recipients2)  # Make sure there are no duplicates
            assert AgentId(type="worker1", key="default") in recipients3
        except Exception as ex:
            raise ex
        finally:
            await subscriptions.stop()
            await worker1.stop()
            await worker1_2.stop()

@pytest.mark.asyncio
async def test_agent_type_register_instance() -> None:
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()

        config_1: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              subscription_topic="subscription",
                                              registry_topic="registry",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_1",
                                              client_id="autogen-client_1")

        worker = KafkaWorkerAgentRuntime(config=config_1)
        await worker.start()

        agent1_id = AgentId(type="name", key="default")
        agentdup_id = AgentId(type="name", key="default")
        agent2_id = AgentId(type="name", key="notdefault")

        agent1 = NoopAgent()
        agent2 = NoopAgent()
        agentdup = NoopAgent()

        await worker.register_agent_instance(agent1, agent_id=agent1_id)
        await worker.register_agent_instance(agent2, agent_id=agent2_id)

        with pytest.raises(ValueError):
            await worker.register_agent_instance(agentdup, agent_id=agentdup_id)

        assert await worker.try_get_underlying_agent_instance(agent1_id, type=NoopAgent) == agent1
        assert await worker.try_get_underlying_agent_instance(agent2_id, type=NoopAgent) == agent2

        await worker.stop()

@pytest.mark.asyncio
async def test_agent_type_register_instance_different_types() -> None:
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()

        config_1: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              subscription_topic="subscription",
                                              registry_topic="registry",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_1",
                                              client_id="autogen-client_1")

        worker = KafkaWorkerAgentRuntime(config=config_1)
        await worker.start()

        agent1_id = AgentId(type="name", key="noop")
        agent2_id = AgentId(type="name", key="loopback")

        agent1 = NoopAgent()
        agent2 = LoopbackAgent()

        await worker.register_agent_instance(agent1, agent_id=agent1_id)
        with pytest.raises(ValueError):
            await worker.register_agent_instance(agent2, agent_id=agent2_id)

        await worker.stop()

@pytest.mark.asyncio
async def test_register_instance_factory() -> None:
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()

        config_1: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              subscription_topic="subscription",
                                              registry_topic="registry",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_1",
                                              client_id="autogen-client_1")

        worker = KafkaWorkerAgentRuntime(config=config_1)
        await worker.start()

        agent1_id = AgentId(type="name", key="default")
        agent1 = NoopAgent()

        await agent1.register_instance(runtime=worker, agent_id=agent1_id)

        with pytest.raises(ValueError):
            await NoopAgent.register(runtime=worker, type="name", factory=lambda: NoopAgent())

        await worker.stop()

@pytest.mark.asyncio
async def test_instance_factory_messaging() -> None:
    loopback_agent_id = AgentId(type="dm_agent", key="dm_agent")
    cascading_agent_id = AgentId(type="instance_agent", key="instance_agent")

    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()

        config_1: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              subscription_topic="subscription",
                                              registry_topic="registry",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_1",
                                              client_id="autogen-client_1")

        worker = KafkaWorkerAgentRuntime(config=config_1)
        await worker.start()

        await asyncio.sleep(2)

        cascading_agent = CascadingAgent(max_rounds=5)
        loopback_agent = LoopbackAgent()

        await loopback_agent.register_instance(worker, agent_id=loopback_agent_id)
        resp = await worker.send_message(message=ContentMessage(content="Hello!"), recipient=loopback_agent_id)
        assert resp == ContentMessage(content="Hello!")

        await cascading_agent.register_instance(worker, agent_id=cascading_agent_id)
        await CascadingAgent.register(worker, "factory_agent", lambda: CascadingAgent(max_rounds=5))

        # instance_agent will publish a message that factory_agent will pick up
        for i in range(5):
            await worker.publish_message(
                CascadingMessageType(round=i + 1), TopicId(type="instance_agent", source="instance_agent")
            )
        await asyncio.sleep(2)

        agent = await worker.try_get_underlying_agent_instance(AgentId("factory_agent", "default"), CascadingAgent)
        assert agent.num_calls == 4
        assert cascading_agent.num_calls == 5

        await worker.stop()

@pytest.mark.asyncio
async def test_register_receives_publish() -> None:
    with KafkaContainer() as kafka:
        connection = kafka.get_bootstrap_server()

        config_1: WorkerConfig = WorkerConfig(title="KafkaWorker",
                                              request_topic="request",
                                              subscription_topic="subscription",
                                              registry_topic="communication",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_1",
                                              client_id="autogen-client_1")
        config_2: WorkerConfig = WorkerConfig(title="KafkaWorker-2",
                                              request_topic="request",
                                              subscription_topic="subscription",
                                              registry_topic="communication",
                                              security_protocol=SecurityProtocol.PLAINTEXT,
                                              security_mechanism=SaslMechanism.PLAIN,
                                              bootstrap_servers=[connection],
                                              group_id="autogen-group_2",
                                              client_id="autogen-client_2")

        worker1 = KafkaWorkerAgentRuntime(config=config_1)
        await worker1.start()

        worker2 = KafkaWorkerAgentRuntime(config=config_2)
        await worker2.start()

        # Let the workers register and discover each other.
        await asyncio.sleep(3)

        worker1.add_message_serializer(try_get_known_serializers_for_type(MessageType))
        await worker1.register_factory(
            type=AgentType("name1"), agent_factory=lambda: LoopbackAgent(), expected_class=LoopbackAgent
        )
        await worker1.add_subscription(TypeSubscription("default", "name1"))

        worker2.add_message_serializer(try_get_known_serializers_for_type(MessageType))
        await worker2.register_factory(
            type=AgentType("name2"), agent_factory=lambda: LoopbackAgent(), expected_class=LoopbackAgent
        )
        await worker2.add_subscription(TypeSubscription("default", "name2"))

        # Publish message from worker1
        await worker1.publish_message(MessageType(), topic_id=TopicId("default", "default"))

        # Let the agent run for a bit.
        await asyncio.sleep(3)

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
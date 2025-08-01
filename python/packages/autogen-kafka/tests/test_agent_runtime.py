import asyncio
from typing import List

import pytest
from autogen_core import try_get_known_serializers_for_type, AgentType, AgentId, TopicId, TypeSubscription, \
    Subscription, DefaultTopicId
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.kafka import KafkaContainer

from autogen_kafka import KafkaAgentRuntimeConfig
from autogen_kafka import SubscriptionService
from autogen_kafka import KafkaAgentRuntime
from autogen_kafka import SchemaRegistryConfig, KafkaConfig
from .utils import LoopbackAgent, MessageType, NoopAgent, CascadingAgent, ContentMessage, CascadingMessageType, \
    LoopbackAgentWithDefaultSubscription


# Test constants
TOPIC_NAMES = {
    "request": "request",
    "subscription": "subscription", 
    "registry": "registry",
    "response": "response",
    "publish": "publish"
}

WORKER_TITLE = "KafkaWorker"
AUTOGEN_GROUP_PREFIX = "autogen-group"
AUTOGEN_CLIENT_PREFIX = "autogen-client"

network: Network = Network().create()

@pytest.fixture
def kafka_network():
    """Fixture that provides Kafka connection string."""
    return network

@pytest.fixture
def kafka_container(kafka_network:Network):
    """Fixture that provides a Kafka container for testing."""
    with (KafkaContainer()
                  .with_network(network)
                  .with_network_aliases("kafka") as kafka):
        yield kafka

@pytest.fixture
def sr_container(kafka_container, kafka_network:Network):
    """Fixture that provides a Kafka container for testing."""
    ip = kafka_container.get_docker_client().bridge_ip(kafka_container.get_wrapped_container().id)
    port = 9092 # Default Kafka port
    with (DockerContainer(image="confluentinc/cp-schema-registry:7.6.0")
                  .with_exposed_ports(8081)
                  .with_network(network)
                  .with_network_aliases("kafka")
                  .with_env("SCHEMA_REGISTRY_HOST_NAME", "schema-registry")
                  .with_env("SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS", f"PLAINTEXT://{ip}:{port}")
                  .with_env("SCHEMA_REGISTRY_LISTENERS", "http://0.0.0.0:8081") as sr_container):
        wait_for_logs(sr_container, "Server started", timeout=30)
        yield sr_container


@pytest.fixture
def kafka_connection(kafka_container):
    """Fixture that provides Kafka connection string."""
    return kafka_container.get_bootstrap_server()

@pytest.fixture
def sr_connection(sr_container):
    """Fixture that provides Kafka connection string."""
    port = sr_container.get_exposed_port(8081)
    return f"http://{sr_container.get_container_host_ip()}:{port}"


def create_worker_config(
    connection: str,
    sr_host: str,
    group_suffix: str, 
    client_suffix: str,
    name: str = WORKER_TITLE
) -> KafkaAgentRuntimeConfig:

    """Helper function to create a WorkerConfig with standard settings."""
    return KafkaAgentRuntimeConfig(
        kafka_config=KafkaConfig(
            name=name + f"_{group_suffix}_{client_suffix}",
            security_protocol="PLAINTEXT",
            security_mechanism="PLAIN",
            bootstrap_servers=[connection],
            group_id=f"{AUTOGEN_GROUP_PREFIX}_{group_suffix}",
            client_id=f"{AUTOGEN_CLIENT_PREFIX}_{client_suffix}",
            schema_registry_config=SchemaRegistryConfig(
                url=sr_host,
            ),
            replication_factor=1
        ),
        request_topic=TOPIC_NAMES["request"],
        subscription_topic=TOPIC_NAMES["subscription"],
        publish_topic=TOPIC_NAMES["publish"],
        registry_topic=TOPIC_NAMES["registry"],
        response_topic=TOPIC_NAMES["response"],
    )


@pytest.fixture
def worker_config_factory(kafka_connection, sr_connection):
    """Fixture that provides a factory for creating worker configs."""
    def _create_config(group_suffix: str = "test", client_suffix: str = "test"):
        return create_worker_config(kafka_connection, sr_connection, group_suffix, client_suffix)
    return _create_config


async def create_started_worker(kafka_connection: str,
                                sr_connection: str,
                                group_suffix: str = "test",
                                client_suffix: str = "test"):
    """Helper function to create and start a worker runtime."""
    config = create_worker_config(kafka_connection, sr_connection, group_suffix, client_suffix)
    worker = KafkaAgentRuntime(config=config)
    await worker.start()
    return worker


async def setup_multiple_workers(kafka_connection: str,
                                 sr_connection: str,
                                 worker_count: int = 2):
    """Helper function to set up multiple workers."""
    workers = []
    for i in range(1, worker_count + 1):
        config = create_worker_config(kafka_connection, sr_connection, str(i), str(i))
        worker = KafkaAgentRuntime(config=config)
        await worker.start()
        await asyncio.sleep(3)  # Allow time for worker to start
        workers.append(worker)
    return workers


async def cleanup_workers(workers: List[KafkaAgentRuntime]):
    """Helper function to clean up multiple workers."""
    for worker in workers:
        await worker.stop()


async def setup_messaging_agents(worker: KafkaAgentRuntime, agent_type: str):
    """Helper function to set up messaging agents."""
    worker.add_message_serializer(try_get_known_serializers_for_type(MessageType))
    await worker.register_factory(
        type=AgentType(agent_type), 
        agent_factory=lambda: LoopbackAgent(), 
        expected_class=LoopbackAgent
    )
    await worker.add_subscription(TypeSubscription("default", agent_type))


async def simulate_worker_disconnect(worker: KafkaAgentRuntime):
    """Helper function to simulate worker disconnect."""
    if worker.is_started is not None:  # type: ignore[reportPrivateUsage]
        try:
            await worker.stop()  # type: ignore[reportPrivateUsage]
        except asyncio.CancelledError:
            pass


# Agent Registration Tests
@pytest.mark.asyncio
async def test_agent_types_must_be_unique_single_worker(kafka_connection, sr_connection):
    """Test that agent types must be unique within a single worker."""
    worker = await create_started_worker(kafka_connection, sr_connection)
    
    try:
        await worker.register_factory(
            type=AgentType("name1"), 
            agent_factory=lambda: NoopAgent(), 
            expected_class=NoopAgent
        )

        with pytest.raises(ValueError):
            await worker.register_factory(
                type=AgentType("name1"), 
                agent_factory=lambda: NoopAgent(), 
                expected_class=NoopAgent
            )

        # These should succeed
        await worker.register_factory(
            type=AgentType("name4"), 
            agent_factory=lambda: NoopAgent(), 
            expected_class=NoopAgent
        )
        await worker.register_factory(
            type=AgentType("name5"), 
            agent_factory=lambda: NoopAgent()
        )
    finally:
        await worker.stop()


@pytest.mark.asyncio
async def test_agent_types_must_be_unique_multiple_workers(kafka_connection, sr_connection):
    """Test that agent types must be unique across multiple workers."""
    workers = await setup_multiple_workers(kafka_connection, sr_connection, 2)
    worker1, worker2 = workers

    try:
        # Allow workers to discover each other
        await asyncio.sleep(3)

        await worker1.register_factory(
            type=AgentType("name1"), 
            agent_factory=lambda: NoopAgent(), 
            expected_class=NoopAgent
        )

        await asyncio.sleep(3)

        with pytest.raises(Exception, match="Agent type name1 already registered"):
            await worker2.register_factory(
                type=AgentType("name1"), 
                agent_factory=lambda: NoopAgent(), 
                expected_class=NoopAgent
            )

        # This should succeed
        await worker2.register_factory(
            type=AgentType("name4"), 
            agent_factory=lambda: NoopAgent(), 
            expected_class=NoopAgent
        )

    finally:
        await cleanup_workers(workers)


@pytest.mark.asyncio
async def test_agent_type_register_instance(kafka_connection, sr_connection):
    """Test registering agent instances."""
    worker = await create_started_worker(kafka_connection, sr_connection)
    
    try:
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
    finally:
        await worker.stop()


@pytest.mark.asyncio
async def test_agent_type_register_instance_different_types(kafka_connection, sr_connection):
    """Test that registering different agent types with same ID fails."""
    worker = await create_started_worker(kafka_connection, sr_connection)
    
    try:
        agent1_id = AgentId(type="name", key="noop")
        agent2_id = AgentId(type="name", key="loopback")

        agent1 = NoopAgent()
        agent2 = LoopbackAgent()

        await worker.register_agent_instance(agent1, agent_id=agent1_id)
        
        with pytest.raises(ValueError):
            await worker.register_agent_instance(agent2, agent_id=agent2_id)
    finally:
        await worker.stop()


@pytest.mark.asyncio
async def test_register_instance_factory(kafka_connection, sr_connection):
    """Test registering both instance and factory for same type fails."""
    worker = await create_started_worker(kafka_connection, sr_connection)
    
    try:
        agent1_id = AgentId(type="name", key="default")
        agent1 = NoopAgent()

        await agent1.register_instance(runtime=worker, agent_id=agent1_id)

        with pytest.raises(ValueError):
            await NoopAgent.register(runtime=worker, type="name", factory=lambda: NoopAgent())
    finally:
        await worker.stop()


# Messaging Tests
@pytest.mark.asyncio
async def test_instance_factory_messaging(kafka_connection, sr_connection):
    """Test messaging between instance and factory agents."""
    loopback_agent_id = AgentId(type="dm_agent", key="dm_agent")
    cascading_agent_id = AgentId(type="instance_agent", key="instance_agent")

    config = create_worker_config(kafka_connection, sr_connection,"1", "1")
    worker = KafkaAgentRuntime(config=config)
    
    try:
        await worker.start()
        await asyncio.sleep(2)

        # Set up agents
        cascading_agent = CascadingAgent(max_rounds=5)
        loopback_agent = LoopbackAgent()

        await loopback_agent.register_instance(worker, agent_id=loopback_agent_id)
        resp = await worker.send_message(
            message=ContentMessage(content="Hello!"), 
            recipient=loopback_agent_id
        )
        assert resp == ContentMessage(content="Hello!")

        await cascading_agent.register_instance(worker, agent_id=cascading_agent_id)
        await CascadingAgent.register(worker, "factory_agent", lambda: CascadingAgent(max_rounds=5))

        # Test message cascading
        for i in range(5):
            await worker.publish_message(
                CascadingMessageType(round=i + 1), 
                TopicId(type="instance_agent", source="instance_agent")
            )
        await asyncio.sleep(5)

        # Verify message processing
        agent = await worker.try_get_underlying_agent_instance(
            AgentId("factory_agent", "default"), CascadingAgent
        )
        assert agent.num_calls == 4
        assert cascading_agent.num_calls == 5

    finally:
        await worker.stop()


@pytest.mark.asyncio
async def test_register_receives_publish(kafka_connection, sr_connection):
    """Test that registered agents receive published messages."""
    workers = await setup_multiple_workers(kafka_connection, sr_connection, 2)
    worker1, worker2 = workers

    try:
        # Let the workers register and discover each other
        await asyncio.sleep(3)

        # Set up message serializers and agents
        await setup_messaging_agents(worker1, "name1")
        await setup_messaging_agents(worker2, "name2")

        # Publish message from worker1
        await worker1.publish_message(
            MessageType(), 
            topic_id=TopicId("default", "default")
        )

        # Let the agents process messages
        await asyncio.sleep(3)

        # Verify message reception in default topic
        worker1_agent = await worker1.try_get_underlying_agent_instance(
            AgentId("name1", "default"), LoopbackAgent
        )
        assert worker1_agent.num_calls == 1
        
        worker2_agent = await worker2.try_get_underlying_agent_instance(
            AgentId("name2", "default"), LoopbackAgent
        )
        assert worker2_agent.num_calls == 1

        # Verify no message reception in other topics
        worker1_agent = await worker1.try_get_underlying_agent_instance(
            AgentId("name1", "other"), LoopbackAgent
        )
        assert worker1_agent.num_calls == 0
        
        worker2_agent = await worker2.try_get_underlying_agent_instance(
            AgentId("name2", "other"), LoopbackAgent
        )
        assert worker2_agent.num_calls == 0

    finally:
        await cleanup_workers(workers)


# Agent Lifecycle Tests
@pytest.mark.asyncio
async def test_disconnected_agent(kafka_connection, sr_connection):
    """Test agent behavior when worker disconnects and reconnects."""
    config_1 = create_worker_config(kafka_connection, sr_connection,"1", "1")
    config_2 = create_worker_config(kafka_connection, sr_connection,"2", "2")
    config_3 = create_worker_config(kafka_connection, sr_connection,"3", "3")

    subscriptions = SubscriptionService(config=config_3)
    worker1 = KafkaAgentRuntime(config=config_1)
    worker1_2 = KafkaAgentRuntime(config=config_2)

    # Helper functions for subscription management
    def get_current_subscriptions() -> List[Subscription]:
        return subscriptions.get_all_subscriptions()  # type: ignore[reportPrivateUsage]

    async def get_subscribed_recipients() -> List[AgentId]:
        return await subscriptions.get_all_subscribed_recipients(DefaultTopicId())  # type: ignore[reportPrivateUsage]

    try:
        await subscriptions.start()
        await worker1.start()
        await asyncio.sleep(3)

        # Register agent and verify initial state
        await LoopbackAgentWithDefaultSubscription.register(
            worker1, "worker1", lambda: LoopbackAgentWithDefaultSubscription()
        )
        await asyncio.sleep(3)

        subscriptions1 = get_current_subscriptions()
        assert len(subscriptions1) == 2
        recipients1 = await get_subscribed_recipients()
        assert AgentId(type="worker1", key="default") in recipients1
        first_subscription_id = subscriptions1[0].id

        # Simulate disconnect
        await worker1.publish_message(ContentMessage(content="Hello!"), DefaultTopicId())
        await simulate_worker_disconnect(worker1)
        await asyncio.sleep(1)

        # Verify cleanup after disconnect
        subscriptions2 = get_current_subscriptions()
        assert len(subscriptions2) == 0
        recipients2 = await get_subscribed_recipients()
        assert len(recipients2) == 0

        # Test reconnect with new worker
        await worker1_2.start()
        await asyncio.sleep(3)
        
        await LoopbackAgentWithDefaultSubscription.register(
            worker1_2, "worker1", lambda: LoopbackAgentWithDefaultSubscription()
        )
        await asyncio.sleep(3)

        # Verify state after reconnect
        subscriptions3 = get_current_subscriptions()
        assert len(subscriptions3) == 2
        assert first_subscription_id not in [x.id for x in subscriptions3]

        recipients3 = await get_subscribed_recipients()
        assert len(set(recipients3)) == len(recipients3)  # No duplicates
        assert AgentId(type="worker1", key="default") in recipients3

    finally:
        await subscriptions.stop()
        await worker1.stop()
        await worker1_2.stop()
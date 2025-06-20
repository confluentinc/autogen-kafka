import asyncio

import pytest
from autogen_core.memory import MemoryContent, MemoryMimeType, ListMemory
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism
from testcontainers.kafka import KafkaContainer

from autogen_kafka_extension.memory.kafka_memory import KafkaMemory
from autogen_kafka_extension.memory.memory_config import MemoryConfig

# Test constants
TOPIC_NAMES = {
    "memory": "memory"
}
WORKER_TITLE = "MemoryWorker"
AUTOGEN_GROUP_PREFIX = "autogen-group"
AUTOGEN_CLIENT_PREFIX = "autogen-client"

@pytest.fixture
def kafka_container():
    """Fixture that provides a Kafka container for testing."""
    with KafkaContainer() as kafka:
        yield kafka

@pytest.fixture
def kafka_connection(kafka_container):
    """Fixture that provides Kafka connection string."""
    return kafka_container.get_bootstrap_server()

@pytest.fixture()
def memory() -> ListMemory:
    return ListMemory()


@pytest.mark.asyncio
async def test_distributed_add(kafka_connection: str, memory: ListMemory):
    session_id = "test"
    kafka_memory = KafkaMemory(
        config=create_worker_config(kafka_connection, "test", "test"),
        session_id=session_id,
        memory=memory
    )
    kafka_memory_2 = KafkaMemory(
        config=create_worker_config(kafka_connection, "test_2", "test_2"),
        session_id=session_id,
        memory=ListMemory()
    )

    await kafka_memory_2.start()
    await kafka_memory.start()
    await asyncio.sleep(3)

    await kafka_memory.add(content = MemoryContent(
        content="test",
        mime_type=MemoryMimeType.TEXT,
        metadata={"source": "test"}
    ))
    result = await kafka_memory.query(query="test")
    assert ( result.results[0].content == "test" )

    await asyncio.sleep(3)

    result = await kafka_memory_2.query(query="test")
    assert ( result.results[0].content == "test" )

@pytest.mark.asyncio
async def test_distributed_add(kafka_connection: str, memory: ListMemory):
    session_id = "test"
    kafka_memory = KafkaMemory(
        config=create_worker_config(kafka_connection, "test", "test"),
        session_id=session_id,
        memory=memory
    )
    await kafka_memory.start()
    await asyncio.sleep(3)

    await kafka_memory.add(content = MemoryContent(
        content="test",
        mime_type=MemoryMimeType.TEXT,
        metadata={"source": "test"}
    ))
    result = await kafka_memory.query(query="test")
    assert ( result.results[0].content == "test" )

    await kafka_memory.clear()

    result = await kafka_memory.query(query="test")
    assert len(result.results) == 0

    kafka_memory = KafkaMemory(
        config=create_worker_config(kafka_connection, "test_2", "test_2"),
        session_id=session_id,
        memory=memory
    )
    await kafka_memory.start()
    await asyncio.sleep(3)

    result = await kafka_memory.query(query="test")
    assert len(result.results) == 0

def create_worker_config(
    connection: str,
    group_suffix: str,
    client_suffix: str,
    name: str = WORKER_TITLE
) -> MemoryConfig:
    """Helper function to create a WorkerConfig with standard settings."""
    return MemoryConfig(
        name=name + f"_{group_suffix}_{client_suffix}",
        memory_topic=TOPIC_NAMES["memory"],
        security_protocol=SecurityProtocol.PLAINTEXT,
        security_mechanism=SaslMechanism.PLAIN,
        bootstrap_servers=[connection],
        group_id=f"{AUTOGEN_GROUP_PREFIX}_{group_suffix}",
        client_id=f"{AUTOGEN_CLIENT_PREFIX}_{client_suffix}"
    )
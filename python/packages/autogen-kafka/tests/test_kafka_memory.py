import asyncio
from typing import Optional
import pytest
from autogen_core.memory import MemoryContent, MemoryMimeType, ListMemory
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.kafka import KafkaContainer

from autogen_kafka import KafkaMemoryConfig
from autogen_kafka.memory.kafka_memory import KafkaMemory
from autogen_kafka.config.services.schema_registry_service import SchemaRegistryConfig

# Test constants
TOPIC_NAMES = {
    "memory": "memory"
}
WORKER_TITLE = "MemoryWorker"
AUTOGEN_GROUP_PREFIX = "autogen-group"
AUTOGEN_CLIENT_PREFIX = "autogen-client"

# Test configuration constants
TEST_SESSION_ID = "test_session"
TEST_CONTENT = "test_content"
TEST_QUERY = "test"
KAFKA_STARTUP_DELAY = 3.0  # seconds to wait for Kafka operations


network: Network = Network().create()

class TestKafkaSMemory:

    @pytest.fixture
    def kafka_network(self):
        """Fixture that provides Kafka connection string."""
        return network

    @pytest.fixture
    def kafka_container(self, kafka_network:Network):
        """Fixture that provides a Kafka container for testing."""
        with (KafkaContainer()
                      .with_network(network)
                      .with_network_aliases("kafka") as kafka):
            yield kafka

    @pytest.fixture
    def sr_container(self, kafka_container, kafka_network:Network):
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
    def kafka_connection(self, kafka_container):
        """Fixture that provides Kafka connection string."""
        return kafka_container.get_bootstrap_server()

    @pytest.fixture
    def sr_connection(self, sr_container):
        """Fixture that provides Kafka connection string."""
        port = sr_container.get_exposed_port(8081)
        return f"http://{sr_container.get_container_host_ip()}:{port}"



    @pytest.fixture
    def memory(self) -> ListMemory:
        """Fixture that provides a fresh ListMemory instance."""
        return ListMemory()

    @pytest.fixture
    def kafka_memory_factory(self, kafka_connection: str, sr_connection: str) -> callable:
        """Factory fixture that creates KafkaMemory instances."""
        def create_kafka_memory(
            group_suffix: str,
            client_suffix: str,
            session_id: str = TEST_SESSION_ID,
            memory: ListMemory | None = None
        ) -> KafkaMemory:
            if memory is None:
                memory = ListMemory()

            config = self.create_worker_config(kafka_connection, sr_connection, group_suffix, client_suffix)
            kafka_memory = KafkaMemory(
                config=config,
                session_id=session_id,
                memory=memory
            )
            return kafka_memory

        return create_kafka_memory

    async def setup_kafka_memory(self, kafka_memory: KafkaMemory) -> None:
        """Helper to start KafkaMemory and wait for initialization."""
        await kafka_memory.start()
        await asyncio.sleep(KAFKA_STARTUP_DELAY)

    async def add_test_content(self, kafka_memory: KafkaMemory, content: str = TEST_CONTENT) -> None:
        """Helper to add test content to KafkaMemory."""
        await kafka_memory.add(
            content=MemoryContent(
                content=content,
                mime_type=MemoryMimeType.TEXT,
                metadata={"source": "test"}
            )
        )

    @pytest.mark.asyncio
    async def test_distributed_add(self, kafka_memory_factory, memory: ListMemory):
        """Test that content added to one KafkaMemory instance is visible to another."""
        # Create two KafkaMemory instances with different configurations
        kafka_memory_1 = kafka_memory_factory("test_1", "test_1", memory=memory)
        kafka_memory_2 = kafka_memory_factory("test_2", "test_2")

        # Start both instances
        await self.setup_kafka_memory(kafka_memory_2)
        await self.setup_kafka_memory(kafka_memory_1)

        # Add content to first instance
        await self.add_test_content(kafka_memory_1)

        # Verify content is available in first instance
        result_1 = await kafka_memory_1.query(query=TEST_QUERY)
        assert len(result_1.results) == 1
        assert result_1.results[0].content == TEST_CONTENT

        # Wait for distribution and verify content is available in second instance
        await asyncio.sleep(KAFKA_STARTUP_DELAY)
        result_2 = await kafka_memory_2.query(query=TEST_QUERY)
        assert len(result_2.results) == 1
        assert result_2.results[0].content == TEST_CONTENT

    @pytest.mark.asyncio
    async def test_clear(self, kafka_memory_factory, memory: ListMemory):
        """Test that clearing memory removes content and persists across instances."""
        # Create and setup first KafkaMemory instance
        kafka_memory_1 = kafka_memory_factory("clear_test_1", "clear_test_1", memory=memory)
        await self.setup_kafka_memory(kafka_memory_1)

        # Add content and verify it exists
        await self.add_test_content(kafka_memory_1)
        result = await kafka_memory_1.query(query=TEST_QUERY)
        assert len(result.results) == 1
        assert result.results[0].content == TEST_CONTENT

        # Clear memory and verify content is removed
        await kafka_memory_1.clear()
        result = await kafka_memory_1.query(query=TEST_QUERY)
        assert len(result.results) == 0

        # Create new instance to verify clear operation persisted
        kafka_memory_2 = kafka_memory_factory("clear_test_2", "clear_test_2", memory=memory)
        await self.setup_kafka_memory(kafka_memory_2)

        # Verify content remains cleared in new instance
        result = await kafka_memory_2.query(query=TEST_QUERY)
        assert len(result.results) == 0

    @pytest.mark.asyncio
    async def test_session_isolation(self, kafka_memory_factory):
        """Test that different session IDs maintain separate memory spaces."""
        session_1 = "session_1"
        session_2 = "session_2"
        content_1 = "content_for_session_1"
        content_2 = "content_for_session_2"

        # Create KafkaMemory instances with different session IDs
        kafka_memory_1 = kafka_memory_factory("session_test_1", "session_test_1", session_id=session_1)
        kafka_memory_2 = kafka_memory_factory("session_test_2", "session_test_2", session_id=session_2)

        await self.setup_kafka_memory(kafka_memory_1)
        await self.setup_kafka_memory(kafka_memory_2)

        # Add different content to each session
        await self.add_test_content(kafka_memory_1, content_1)
        await self.add_test_content(kafka_memory_2, content_2)

        # Wait for distribution
        await asyncio.sleep(KAFKA_STARTUP_DELAY)

        # Verify each session only sees its own content
        result_1 = await kafka_memory_1.query(query="content")
        result_2 = await kafka_memory_2.query(query="content")

        assert len(result_1.results) == 1
        assert result_1.results[0].content == content_1

        assert len(result_2.results) == 1
        assert result_2.results[0].content == content_2

        # Verify cross-session isolation
        result_1_cross = await kafka_memory_1.query(query=content_2)
        result_2_cross = await kafka_memory_2.query(query=content_1)

        assert result_1_cross.results[0].content != content_2
        assert result_2_cross.results[0].content != content_1


    @pytest.mark.asyncio
    async def test_concurrent_operations(self, kafka_memory_factory, memory: ListMemory):
        """Test concurrent add operations from multiple instances."""
        session_id = "concurrent_test"

        # Create multiple KafkaMemory instances
        kafka_memory_1 = kafka_memory_factory("concurrent_1", "concurrent_1", session_id=session_id, memory=memory)
        kafka_memory_2 = kafka_memory_factory("concurrent_2", "concurrent_2", session_id=session_id)
        kafka_memory_3 = kafka_memory_factory("concurrent_3", "concurrent_3", session_id=session_id)

        # Start all instances
        await asyncio.gather(
            self.setup_kafka_memory(kafka_memory_1),
            self.setup_kafka_memory(kafka_memory_2),
            self.setup_kafka_memory(kafka_memory_3)
        )

        # Add content concurrently from different instances
        contents = ["concurrent_content_1", "concurrent_content_2", "concurrent_content_3"]
        await asyncio.gather(
            self.add_test_content(kafka_memory_1, contents[0]),
            self.add_test_content(kafka_memory_2, contents[1]),
            self.add_test_content(kafka_memory_3, contents[2])
        )

        # Wait for all operations to propagate
        await asyncio.sleep(KAFKA_STARTUP_DELAY)

        # Verify all content is available in all instances
        for kafka_memory in [kafka_memory_1, kafka_memory_2, kafka_memory_3]:
            result = await kafka_memory.query(query="concurrent")
            assert len(result.results) == 3
            retrieved_contents = {r.content for r in result.results}
            assert retrieved_contents == set(contents)

    @pytest.mark.asyncio
    async def test_metadata_handling(self, kafka_memory_factory, memory: ListMemory):
        """Test that metadata is properly stored and retrieved."""
        kafka_memory = kafka_memory_factory("metadata_test", "metadata_test", memory=memory)
        await self.setup_kafka_memory(kafka_memory)

        # Add content with custom metadata
        custom_metadata = {
            "source": "test_source",
            "timestamp": "2024-01-01T00:00:00Z",
            "priority": "high",
            "tags": ["test", "metadata"]
        }

        await kafka_memory.add(
            content=MemoryContent(
                content="content_with_metadata",
                mime_type=MemoryMimeType.TEXT,
                metadata=custom_metadata
            )
        )

        # Query and verify metadata is preserved
        result = await kafka_memory.query(query="metadata")
        assert len(result.results) == 1

        retrieved_content = result.results[0]
        assert retrieved_content.content == "content_with_metadata"
        assert retrieved_content.metadata == custom_metadata

    @pytest.mark.asyncio
    async def test_query_edge_cases(self, kafka_memory_factory, memory: ListMemory):
        """Test various query scenarios and edge cases."""
        kafka_memory = kafka_memory_factory("query_test", "query_test", memory=memory)
        await self.setup_kafka_memory(kafka_memory)

        # Test empty query on empty memory
        result = await kafka_memory.query(query="")
        assert len(result.results) == 0

        # Test query on non-existent content
        result = await kafka_memory.query(query="non_existent")
        assert len(result.results) == 0

        # Add some test content
        test_contents = [
            "The quick brown fox jumps over the lazy dog",
            "Python is a great programming language",
            "Kafka enables real-time data streaming",
            "Unit testing ensures code quality"
        ]

        for content in test_contents:
            await kafka_memory.add(
                content=MemoryContent(
                    content=content,
                    mime_type=MemoryMimeType.TEXT,
                    metadata={"source": "test"}
                )
            )

        # Test partial word matching
        result = await kafka_memory.query(query="Python")
        assert len(result.results) >= 1
        assert any("Python" in r.content for r in result.results)

        # Test case sensitivity (assuming query is case-insensitive)
        result = await kafka_memory.query(query="python")
        assert len(result.results) >= 1

        # Test empty query on populated memory
        result = await kafka_memory.query(query="")
        # Should return all results or no results depending on implementation
        assert isinstance(result.results, list)

    @pytest.mark.asyncio
    async def test_different_mime_types(self, kafka_memory_factory, memory: ListMemory):
        """Test handling of different MIME types."""
        kafka_memory = kafka_memory_factory("mime_test", "mime_test", memory=memory)
        await self.setup_kafka_memory(kafka_memory)

        # Add content with different MIME types
        contents = [
            MemoryContent(
                content="Plain text content",
                mime_type=MemoryMimeType.TEXT,
                metadata={"type": "text"}
            ),
            MemoryContent(
                content='{"key": "value", "number": 42}',
                mime_type=MemoryMimeType.JSON,
                metadata={"type": "json"}
            ),
            MemoryContent(
                content="# Markdown Header\n\nThis is **bold** text.",
                mime_type=MemoryMimeType.MARKDOWN,
                metadata={"type": "markdown"}
            )
        ]

        # Add all content types
        for content in contents:
            await kafka_memory.add(content=content)

        # Query and verify all types are stored correctly
        result = await kafka_memory.query(query="content")
        assert len(result.results) >= len(contents)

        # Verify MIME types are preserved
        mime_types = {r.mime_type for r in result.results}
        expected_mime_types = {c.mime_type for c in contents}
        assert expected_mime_types.issubset(mime_types)

    @pytest.mark.asyncio
    async def test_large_content(self, kafka_memory_factory, memory: ListMemory):
        """Test handling of larger content sizes."""
        kafka_memory = kafka_memory_factory("large_content_test", "large_content_test", memory=memory)
        await self.setup_kafka_memory(kafka_memory)

        # Create large content (1KB)
        large_content = "Large content test. " * 50  # ~1KB

        await kafka_memory.add(
            content=MemoryContent(
                content=large_content,
                mime_type=MemoryMimeType.TEXT,
                metadata={"size": "large"}
            )
        )

        # Verify large content is stored and retrieved correctly
        result = await kafka_memory.query(query="Large content")
        assert len(result.results) == 1
        assert result.results[0].content == large_content
        assert result.results[0].metadata["size"] == "large"

    @pytest.mark.asyncio
    async def test_multiple_add_same_session(self, kafka_memory_factory, memory: ListMemory):
        """Test adding multiple pieces of content to the same session."""
        kafka_memory = kafka_memory_factory("multi_add_test", "multi_add_test", memory=memory)
        await self.setup_kafka_memory(kafka_memory)

        # Add multiple pieces of content
        contents = [
            "First piece of content",
            "Second piece of content",
            "Third piece of content"
        ]

        for i, content in enumerate(contents):
            await kafka_memory.add(
                content=MemoryContent(
                    content=content,
                    mime_type=MemoryMimeType.TEXT,
                    metadata={"order": i, "total": len(contents)}
                )
            )

        # Query for all content
        result = await kafka_memory.query(query="content")
        assert len(result.results) == len(contents)

        # Verify all content is present
        retrieved_contents = {r.content for r in result.results}
        assert retrieved_contents == set(contents)

        # Verify metadata is preserved
        orders = {r.metadata["order"] for r in result.results}
        assert orders == {0, 1, 2}

    @pytest.mark.asyncio
    async def test_memory_persistence_across_restarts(self, kafka_memory_factory, memory: ListMemory):
        """Test that memory persists when KafkaMemory instances are restarted."""
        session_id = "persistence_test"

        # Create first instance and add content
        kafka_memory_1 = kafka_memory_factory("persist_1", "persist_1", session_id=session_id, memory=memory)
        await self.setup_kafka_memory(kafka_memory_1)

        persistent_content = "This content should persist"
        await kafka_memory_1.add(
            content=MemoryContent(
                content=persistent_content,
                mime_type=MemoryMimeType.TEXT,
                metadata={"persistent": True}
            )
        )

        # Verify content exists
        result = await kafka_memory_1.query(query="persist")
        assert len(result.results) == 1
        assert result.results[0].content == persistent_content

        # Simulate restart by creating new instance with same session
        kafka_memory_2 = kafka_memory_factory("persist_2", "persist_2", session_id=session_id)
        await self.setup_kafka_memory(kafka_memory_2)

        # Verify content persists in new instance
        result = await kafka_memory_2.query(query="persist")
        assert len(result.results) == 1
        assert result.results[0].content == persistent_content
        assert result.results[0].metadata["persistent"] is True

    def create_worker_config(
        self,
        connection: str,
        sr_connection: str,
        group_suffix: str,
        client_suffix: str,
        name: str = WORKER_TITLE
    ) -> KafkaMemoryConfig:
        """Helper function to create a MemoryConfig with standard settings."""
        return KafkaMemoryConfig(
            name=f"{name}_{group_suffix}_{client_suffix}",
            security_protocol=SecurityProtocol.PLAINTEXT,
            security_mechanism=SaslMechanism.PLAIN,
            bootstrap_servers=[connection],
            group_id=f"{AUTOGEN_GROUP_PREFIX}_{group_suffix}",
            client_id=f"{AUTOGEN_CLIENT_PREFIX}_{client_suffix}",
            schema_registry_config=SchemaRegistryConfig(url=sr_connection),
            memory_topic=TOPIC_NAMES["memory"],
        )
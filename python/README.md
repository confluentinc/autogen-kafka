# AutoGen Kafka Extension - Python Implementation

A scalable, event-driven Python runtime for autonomous agents powered by Apache Kafka. The `KafkaWorkerAgentRuntime` extends AutoGen's core `AgentRuntime` to enable message-based communication over Kafka topics, with built-in support for pub/sub and RPC-style patterns.

---

## 📌 Features

- **Agent Lifecycle Management** – Dynamically register agent factories and instances
- **Kafka Message Routing** – Built-in pub/sub and RPC using Kafka topics
- **Distributed Memory** – Kafka-based memory sharing across agent instances with session isolation
- **Streaming Engine** – Uses `kstreams` for asynchronous event processing
- **Serialization & Schema Support** – JSON and CloudEvents-based payloads
- **Observability** – Integrated OpenTelemetry tracing for monitoring and debugging
- **Fault Handling** – Safe background task management with traceable errors
- **Scalable Architecture** – Designed for distributed, high-throughput environments

---

## 📋 Requirements

- **Python**: 3.10 or higher
- **Apache Kafka**: Local cluster or managed service (e.g., Confluent Cloud)
- **UV**: Recommended for dependency management

### Core Dependencies
- `autogen-core>=0.6.1` - Core AutoGen framework
- `autogen>=0.1.0` - AutoGen library
- `confluent-kafka>=2.10.1` - Kafka Python client
- `kstreams>=0.26.9` - Kafka Streams abstraction for Python
- `cloudevents>=1.12.0` - CloudEvents specification support
- `aiorun>=2025.1.1` - Async runtime management

### Development Dependencies
- `pytest>=8.4.0` - Testing framework
- `pytest-asyncio>=1.0.0` - Async testing support
- `testcontainers>=4.10.0` - Integration testing with Kafka containers

---

## 🚀 Installation and Setup

### 1. Install Dependencies

Navigate to the Python directory and install using UV:

```bash
cd python
uv sync --all-extras
```

Alternatively, use pip:

```bash
pip install -e packages/autogen-kafka-extension/
```

### 2. Kafka Setup

Ensure your Kafka cluster is running and accessible. For local development, you can run Kafka using the provided Docker Compose:

```bash
# Start Kafka and dependencies (from project root)
cd ..
docker-compose up -d

# Verify Kafka is running
docker-compose ps
```

For production environments, configure your `WorkerConfig` to connect to your managed Kafka service (e.g., Confluent Cloud, Amazon MSK).

### 3. Basic Configuration and Startup

Here's a simple example to get the runtime started:

```python
import asyncio
from autogen_kafka_extension.runtimes.worker_config import WorkerConfig
from autogen_kafka_extension.runtimes.worker_runtime import KafkaWorkerAgentRuntime


async def main():
   # Configure the runtime
   config = WorkerConfig(
      request_topic="agent.requests",
      subscription_topic="agent.responses",
      group_id="worker-group",
      client_id="worker-client",
      title="Python Agent Runtime"
   )

   # Create and start the runtime
   runtime = KafkaWorkerAgentRuntime(config)
   await runtime.start()

   # Runtime is now ready for agent registration and messaging
   return runtime


if __name__ == "__main__":
   runtime = asyncio.run(main())
```

---

## 🛠 Agent Management

### Registering a Factory

Register agent factories to enable dynamic agent creation:

```python
from autogen_core.agent import Agent, AgentId
from autogen_core.message import Message

class EchoAgent(Agent):
    """Simple echo agent for demonstration."""
    
    async def on_message(self, message: Message, ctx) -> Message:
        return Message(content=f"Echo: {message.content}")

# Register a factory for creating Echo agents
await runtime.register_factory("echo", lambda: EchoAgent())

# The runtime can now create Echo agents on demand
```

### Registering a Specific Instance

For more control, register specific agent instances:

```python
# Create and register a specific agent instance
agent_id = AgentId("echo", "instance-001")
echo_agent = EchoAgent()
await runtime.register_agent_instance(echo_agent, agent_id)
```

### Agent Configuration Options

```python
# Register with additional metadata
await runtime.register_factory(
    "advanced_agent", 
    lambda: AdvancedAgent(),
    metadata={"version": "1.0", "capabilities": ["nlp", "reasoning"]}
)
```

---

## 📤 Messaging Patterns

### Send a Message (RPC-style)

Send messages directly to specific agents with response handling:

```python
from autogen_core.agent import AgentId

# Send a message and wait for response
response = await runtime.send_message(
    "Hello, how are you?", 
    recipient=AgentId("echo", "instance-001")
)
print(f"Response: {response}")

# Send with timeout
try:
    response = await asyncio.wait_for(
        runtime.send_message("Query", recipient=AgentId("echo", "instance-001")),
        timeout=5.0
    )
except asyncio.TimeoutError:
    print("Message timed out")
```

### Publish a Message (Broadcast)

Broadcast messages to all subscribers of a topic:

```python
from autogen_core.topic import TopicId

# Publish to all subscribers of the topic
await runtime.publish_message(
    "System announcement: Maintenance at 2 AM", 
    topic_id=TopicId("event", "system-broadcast")
)

# Publish with custom headers
await runtime.publish_message(
    "Critical alert",
    topic_id=TopicId("alerts", "critical"),
    metadata={"priority": "high", "source": "monitoring"}
)
```

### Subscribe to Topics

Set up agents to listen for specific topic messages:

```python
from autogen_core.subscription import Subscription

class AlertAgent(Agent):
    """Agent that processes alert messages."""
    
    async def on_message(self, message: Message, ctx) -> None:
        # Process the alert
        print(f"Alert received: {message.content}")

# Register agent with topic subscription
await runtime.register_factory(
    "alert_processor",
    lambda: AlertAgent(),
    subscriptions=[
        Subscription(topic_type="alerts", topic_source="critical")
    ]
)
```

---

## 🧠 Distributed Memory with Kafka

The AutoGen Kafka Extension provides a distributed memory implementation (`KafkaMemory`) that uses Apache Kafka for persistence and synchronization across multiple agent instances. This enables agents to share memory state in distributed environments.

### Key Features

- **Distributed Memory Sharing**: Multiple agent instances can share the same memory state
- **Kafka-based Persistence**: Memory content is stored in Kafka topics for durability
- **Session-based Isolation**: Different sessions maintain separate memory spaces
- **Event-driven Synchronization**: Real-time memory updates across instances
- **Async Context Manager**: Proper resource management and cleanup
- **Multiple Content Types**: Support for text, JSON, images, and binary content

### Basic Usage

```python
import asyncio
from autogen_core.memory import MemoryContent, MemoryMimeType
from autogen_kafka_extension.memory.kafka_memory import KafkaMemory
from autogen_kafka_extension.memory.memory_config import MemoryConfig

async def setup_distributed_memory():
    # Configure Kafka memory
    config = MemoryConfig(
        name="memory-worker",
        group_id="memory-group",
        client_id="memory-client",
        bootstrap_servers=["localhost:9092"],
        memory_topic="agent-memory"
    )
    
    # Create memory instance with session isolation
    session_id = "agent-session-001"
    
    # Option 1: Using async context manager (recommended)
    async with KafkaMemory(config, session_id) as memory:
        # Memory is automatically started and will be cleaned up
        # Add content to memory
        await memory.add(MemoryContent(
            content="Important conversation context",
            mime_type=MemoryMimeType.TEXT,
            metadata={"source": "conversation", "timestamp": "2024-01-01"}
        ))
        
        # Query memory
        result = await memory.query("conversation")
        print(f"Found {len(result.results)} relevant memories")
        
        # Memory is automatically synchronized across all instances
        # with the same session_id
        
    # Memory is properly cleaned up when exiting context
    
    # Option 2: Manual start/close (for long-lived instances)
    memory = KafkaMemory(config, session_id)
    await memory.start()  # Must call start() explicitly
    
    try:
        # Use memory...
        await memory.add(MemoryContent(
            content="Another memory entry",
            mime_type=MemoryMimeType.TEXT
        ))
        result = await memory.query("memory")
        print(f"Found {len(result.results)} memories")
    finally:
        await memory.close()  # Must call close() explicitly
```

### Advanced Memory Configuration

```python
from autogen_core.memory import ListMemory

# Use custom underlying memory implementation
custom_memory = ListMemory()

config = MemoryConfig(
    name="advanced-memory",
    group_id="memory-group",
    client_id="memory-client-001",
    bootstrap_servers=["kafka-cluster:9092"],
    memory_topic="agent-memory",
    replication_factor=3,  # For production environments
    
    # Kafka security settings
    security_protocol="SASL_SSL",
    security_mechanism="PLAIN",
    sasl_plain_username="your_username",
    sasl_plain_password="your_password"
)

async with KafkaMemory(config, "production-session", memory=custom_memory) as memory:
    # Memory is automatically started when entering context
    # Advanced memory operations
    await memory.add(MemoryContent(
        content="Production data",
        mime_type=MemoryMimeType.TEXT,
        metadata={"environment": "prod"}
    ))
    
    # Memory will be automatically closed when exiting context
```

### Multi-Instance Memory Sharing

```python
async def demonstrate_distributed_memory():
    """Show how multiple instances share memory state."""
    
    config = MemoryConfig(
        name="shared-memory",
        group_id="memory-group",
        client_id="instance-1",
        bootstrap_servers=["localhost:9092"],
        memory_topic="shared-memory"
    )
    
    session_id = "shared-session"
    
    # Instance 1: Add content
    async with KafkaMemory(config, session_id) as memory1:
        # Memory1 is automatically started
        await memory1.add(MemoryContent(
            content="Shared knowledge base entry",
            mime_type=MemoryMimeType.TEXT,
            metadata={"category": "facts"}
        ))
        
        # Configure second instance
        config2 = MemoryConfig(
            name="shared-memory",
            group_id="memory-group",
            client_id="instance-2",  # Different client
            bootstrap_servers=["localhost:9092"],
            memory_topic="shared-memory"
        )
        
        # Instance 2: Access same memory
        async with KafkaMemory(config2, session_id) as memory2:
            # Memory2 is automatically started and syncs with memory1
            # Content added by instance1 is available here
            result = await memory2.query("knowledge")
            assert len(result.results) > 0
            print("Memory successfully shared between instances!")
```

### Session Isolation

```python
async def demonstrate_session_isolation():
    """Show how different sessions maintain separate memory spaces."""
    
    config = MemoryConfig(
        name="isolated-memory",
        group_id="memory-group",
        client_id="client",
        bootstrap_servers=["localhost:9092"],
        memory_topic="isolated-memory"
    )
    
    # Two different sessions
    session_a = "session-a"
    session_b = "session-b"
    
    # Add content to session A
    async with KafkaMemory(config, session_a) as memory_a:
        await memory_a.add(MemoryContent(
            content="Session A private data",
            mime_type=MemoryMimeType.TEXT
        ))
    
    # Add different content to session B
    async with KafkaMemory(config, session_b) as memory_b:
        await memory_b.add(MemoryContent(
            content="Session B private data",
            mime_type=MemoryMimeType.TEXT
        ))
        
        # Sessions cannot access each other's data
        result = await memory_b.query("Session A")
        assert len(result.results) == 0  # No cross-session access
```

### Content Types and Metadata

```python
from autogen_core import Image
import json

async def demonstrate_content_types():
    """Show support for various content types."""
    
    config = MemoryConfig(
        name="content-memory",
        group_id="memory-group", 
        client_id="content-client",
        bootstrap_servers=["localhost:9092"],
        memory_topic="content-memory"
    )
    
    async with KafkaMemory(config, "content-session") as memory:
        # Text content
        await memory.add(MemoryContent(
            content="This is text content",
            mime_type=MemoryMimeType.TEXT,
            metadata={"type": "note", "priority": "high"}
        ))
        
        # JSON content
        await memory.add(MemoryContent(
            content={"key": "value", "data": [1, 2, 3]},
            mime_type=MemoryMimeType.JSON,
            metadata={"schema_version": "1.0"}
        ))
        
        # Image content
        image = Image.from_base64("base64_encoded_image_data")
        await memory.add(MemoryContent(
            content=image,
            mime_type=MemoryMimeType.IMAGE,
            metadata={"format": "png", "size": "1024x768"}
        ))
        
        # Binary content
        await memory.add(MemoryContent(
            content=b"binary data",
            mime_type=MemoryMimeType.BINARY,
            metadata={"encoding": "raw"}
        ))
```

### Integration with Agent Runtime

```python
from autogen_core.agent import Agent
from autogen_kafka_extension.runtimes.worker_runtime import KafkaWorkerAgentRuntime

class MemoryEnabledAgent(Agent):
    """Agent that uses distributed Kafka memory."""
    
    def __init__(self, memory: KafkaMemory):
        self._memory = memory
    
    async def on_message(self, message, ctx):
        # Store conversation in distributed memory
        await self._memory.add(MemoryContent(
            content=f"Conversation: {message.content}",
            mime_type=MemoryMimeType.TEXT,
            metadata={"timestamp": str(ctx.timestamp)}
        ))
        
        # Query relevant memories
        relevant = await self._memory.query(message.content)
        
        # Use memory context in response
        context = "\n".join([mem.content for mem in relevant.results])
        response = f"Based on memory: {context}\nResponse: {message.content}"
        
        return response

# Setup runtime with memory-enabled agents
async def setup_memory_enabled_runtime():
    # Setup runtime
    runtime_config = WorkerConfig(
        request_topic="agent.requests",
        subscription_topic="agent.responses",
        group_id="runtime-group",
        client_id="runtime-client"
    )
    
    runtime = KafkaWorkerAgentRuntime(runtime_config)
    
    # Setup shared memory
    memory_config = MemoryConfig(
        name="agent-memory",
        group_id="memory-group",
        client_id="memory-client",
        bootstrap_servers=["localhost:9092"],
        memory_topic="agent-shared-memory"
    )
    
    memory = KafkaMemory(memory_config, "agent-session")
    await memory.start()
    
    # Register memory-enabled agent
    await runtime.register_factory(
        "memory_agent",
        lambda: MemoryEnabledAgent(memory)
    )
    
    await runtime.start()
    return runtime, memory
```

### Memory Management Operations

```python
async def memory_management_examples():
    """Examples of memory management operations."""
    
    config = MemoryConfig(
        name="mgmt-memory",
        group_id="memory-group",
        client_id="mgmt-client", 
        bootstrap_servers=["localhost:9092"],
        memory_topic="management-memory"
    )
    
    async with KafkaMemory(config, "mgmt-session") as memory:
        # Add multiple entries
        for i in range(5):
            await memory.add(MemoryContent(
                content=f"Entry {i}",
                mime_type=MemoryMimeType.TEXT,
                metadata={"index": i}
            ))
        
        # Query all entries
        all_entries = await memory.query("Entry")
        print(f"Total entries: {len(all_entries.results)}")
        
        # Clear all memory (synchronized across instances)
        await memory.clear()
        
        # Verify memory is cleared
        after_clear = await memory.query("Entry")
        assert len(after_clear.results) == 0
        print("Memory successfully cleared")
```

### Best Practices

- **Memory Initialization**: Always start KafkaMemory before use - either with `async with` context manager (recommended) or explicit `await memory.start()`
- **Session Management**: Use meaningful session IDs to organize memory by conversation, user, or task context
- **Memory Cleanup**: Always use async context managers or explicitly call `close()` for proper cleanup
- **Content Organization**: Use metadata fields to organize and categorize memory content
- **Performance**: Consider memory size and query patterns when designing your memory strategy
- **Security**: Ensure proper Kafka security configuration for sensitive memory content
- **Monitoring**: Monitor Kafka topic size and consumer lag for memory performance insights

---

## ⚙️ Configuration Options

The `WorkerConfig` class provides extensive configuration options:

### Basic Configuration

```python
config = WorkerConfig(
    # Core Kafka settings
    request_topic="agent.requests",
    subscription_topic="agent.responses",
    group_id="worker-group",
    client_id="worker-client",
    
    # Runtime settings
    title="My Agent Runtime",
    description="Production agent runtime",
    
    # Kafka connection settings
    bootstrap_servers="localhost:9092",
    security_protocol="PLAINTEXT",
)
```

### Advanced Configuration

```python
from autogen_kafka_extension.runtimes.worker_config import KafkaConfig

# Advanced Kafka configuration
kafka_config = KafkaConfig(
   bootstrap_servers="kafka-cluster:9092",
   security_protocol="SASL_SSL",
   sasl_mechanism="PLAIN",
   sasl_username="your_username",
   sasl_password="your_password",

   # Performance tuning
   batch_size=16384,
   linger_ms=100,
   compression_type="gzip",

   # Consumer settings
   session_timeout_ms=30000,
   heartbeat_interval_ms=10000,
   max_poll_records=500,
)

config = WorkerConfig(
   request_topic="agent.requests",
   subscription_topic="agent.responses",
   group_id="worker-group",
   client_id="worker-client",
   kafka_config=kafka_config
)
```

### Environment-based Configuration

```python
import os

config = WorkerConfig(
    request_topic=os.getenv("KAFKA_REQUEST_TOPIC", "agent.requests"),
    subscription_topic=os.getenv("KAFKA_RESPONSE_TOPIC", "agent.responses"),
    group_id=os.getenv("KAFKA_GROUP_ID", "worker-group"),
    client_id=os.getenv("KAFKA_CLIENT_ID", "worker-client"),
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
)
```

---

## 🧪 Testing

### Running Tests

The package includes comprehensive test coverage:

```bash
cd packages/autogen-kafka-extension

# Run all tests
PYTHONPATH=tests:src uv run python -m pytest tests/

# Run specific test file
PYTHONPATH=tests:src uv run python -m pytest tests/test_worker_runtime.py

# Run with coverage
PYTHONPATH=tests:src uv run python -m pytest tests/ --cov=autogen_kafka_extension

# Run with verbose output
PYTHONPATH=tests:src uv run python -m pytest tests/ -v

# Run specific test categories
PYTHONPATH=tests:src uv run python -m pytest tests/test_kafka_memory.py -v  # Memory tests
PYTHONPATH=tests:src uv run python -m pytest tests/test_worker_runtime.py -v  # Runtime tests

# Use the provided test script
./run_tests.sh
```

### Integration Testing

The tests use testcontainers to spin up real Kafka instances:

```python
import pytest
from testcontainers.kafka import KafkaContainer

@pytest.fixture(scope="session")
def kafka_container():
    with KafkaContainer() as kafka:
        yield kafka

async def test_runtime_with_real_kafka(kafka_container):
    config = WorkerConfig(
        bootstrap_servers=kafka_container.get_bootstrap_server(),
        request_topic="test.requests",
        subscription_topic="test.responses",
        group_id="test-group",
        client_id="test-client"
    )
    
    runtime = KafkaWorkerAgentRuntime(config)
    await runtime.start()
    # Test runtime functionality
```

### Performance Testing

```bash
# Run performance benchmarks
PYTHONPATH=tests:src uv run python -m pytest tests/test_performance.py -v

# Generate performance report
PYTHONPATH=tests:src uv run python -m pytest tests/ --benchmark-only
```

---

## 📦 Development Notes

### Architecture Components

- **`KafkaWorkerAgentRuntime`**: Main runtime class extending AutoGen's AgentRuntime
- **`KafkaMemory`**: Distributed memory implementation using Kafka for persistence and synchronization
- **`StreamingService`**: Kafka stream processing using kstreams
- **`MessageProcessor`**: Handles message routing and processing logic
- **`AgentRegistry`**: Manages agent factory and instance registration
- **`BackgroundTaskManager`**: Robust background task management
- **`MessageSerDes`**: CloudEvents-based message serialization

### Code Structure

```
src/autogen_kafka_extension/
├── runtimes/                   # Runtime implementations
│   ├── worker_runtime.py       # Main runtime implementation
│   ├── worker_config.py        # Configuration classes
│   ├── messaging_client.py     # Kafka messaging client
│   └── services/               # Runtime services
│       ├── agent_manager.py    # Agent lifecycle management
│       ├── agent_registry.py   # Agent registration management
│       ├── background_task_manager.py  # Background task handling
│       ├── message_processor.py # Message processing logic
│       ├── subscription_service.py # Subscription management
│       └── constants.py        # Shared constants
├── memory/                     # Distributed memory implementation
│   ├── kafka_memory.py         # Main memory class with Kafka persistence
│   └── memory_config.py        # Memory configuration
├── shared/                     # Shared components
│   ├── streaming_service.py    # Kafka streaming service
│   ├── streaming_worker_base.py # Base streaming worker
│   ├── topic_admin_service.py  # Kafka topic administration
│   ├── kafka_config.py         # Kafka configuration
│   └── events/                 # Event handling and serialization
│       ├── events_serdes.py    # Event serialization/deserialization
│       ├── memory_event.py     # Memory event structures
│       ├── request_event.py    # Request event structures
│       ├── response_event.py   # Response event structures
│       ├── subscription_event.py # Subscription events
│       └── registration_event.py # Registration events
└── py.typed                    # Type checking support
```

### Debugging and Monitoring

- **OpenTelemetry Integration**: Built-in tracing for message flow visibility
- **Structured Logging**: Comprehensive logging throughout the runtime lifecycle  
- **Error Handling**: Graceful error recovery with detailed error reporting
- **Health Checks**: Runtime health monitoring and diagnostics

### Custom Extensions

#### Custom Message Serialization

```python
from autogen_kafka_extension.shared.events import MessageSerDes


class CustomSerDes(MessageSerDes):
   """Custom message serialization for specific use cases."""

   def serialize(self, message: Message) -> bytes:
      # Implement custom serialization
      pass

   def deserialize(self, data: bytes) -> Message:
      # Implement custom deserialization
      pass


# Use custom serializer
runtime = KafkaWorkerAgentRuntime(config, message_serdes=CustomSerDes())
```

#### Custom Agent Middleware

```python
from autogen_kafka_extension.runtimes.services.message_processor import MessageProcessor


class CustomMessageProcessor(MessageProcessor):
   """Custom message processing with additional middleware."""

   async def process_message(self, message: Message, context) -> Message:
      # Add custom preprocessing
      message = await self.preprocess(message)

      # Call parent processing
      result = await super().process_message(message, context)

      # Add custom postprocessing
      return await self.postprocess(result)
```

---

## 🏗️ Advanced Usage

### Scaling Considerations

- **Consumer Groups**: Use Kafka consumer groups for horizontal scaling
- **Topic Partitioning**: Design topic partitioning strategy for optimal load distribution
- **Resource Management**: Monitor memory and CPU usage for optimal performance

```python
# Configure for high-throughput scenarios
config = WorkerConfig(
    # ... basic config ...
    kafka_config=KafkaConfig(
        batch_size=65536,           # Larger batches for throughput
        linger_ms=100,              # Batch aggregation time
        compression_type="lz4",     # Fast compression
        max_poll_records=1000,      # Process more records per poll
        fetch_min_bytes=1024,       # Reduce network calls
    )
)
```

### Agent State Management

```python
class StatefulAgent(Agent):
    """Agent with persistent state management."""
    
    def __init__(self):
        self.state = {}
        self.state_store = StateStore()  # Custom state persistence
    
    async def on_message(self, message: Message, ctx) -> Message:
        # Load state
        self.state = await self.state_store.load(self.id)
        
        # Process message
        result = await self.process_with_state(message)
        
        # Save state
        await self.state_store.save(self.id, self.state)
        
        return result
```

### Multi-Runtime Coordination

```python
# Deploy multiple runtime instances for load distribution
async def deploy_runtime_cluster():
    runtimes = []
    
    for i in range(3):  # Deploy 3 runtime instances
        config = WorkerConfig(
            group_id=f"worker-group-{i}",
            client_id=f"worker-client-{i}",
            # ... other config
        )
        
        runtime = KafkaWorkerAgentRuntime(config)
        await runtime.start()
        runtimes.append(runtime)
    
    return runtimes
```

---

## 📈 Roadmap

### Completed Features
- [x] Core Kafka integration with AutoGen
- [x] CloudEvents support for message format
- [x] OpenTelemetry tracing integration
- [x] Comprehensive test coverage with testcontainers
- [x] Agent factory and instance registration
- [x] Pub/sub and RPC messaging patterns
- [x] Distributed Kafka-based memory with session isolation

### In Progress
- [ ] Performance optimizations for high-throughput scenarios
- [ ] Advanced CLI tools for monitoring and debugging
- [ ] Enhanced memory query capabilities and indexing

### Planned Features
- [ ] Agent metadata and discovery service
- [ ] Pluggable metrics exporters (Prometheus, StatsD)
- [ ] Schema registry integration for advanced serialization
- [ ] Dead letter queue support for error handling
- [ ] Docker images and Kubernetes deployment manifests
- [ ] Advanced security features (encryption, authentication)

---

## 🐛 Troubleshooting

### Common Issues

1. **Kafka Connection Issues**
   ```python
   # Verify connection
   from kafka import KafkaProducer
   
   producer = KafkaProducer(
       bootstrap_servers=['localhost:9092'],
       value_serializer=lambda x: x.encode('utf-8')
   )
   producer.send('test-topic', 'test-message')
   producer.flush()
   ```

2. **Agent Registration Problems**
   ```python
   # Debug agent registration
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   # Check if factory is registered
   factories = await runtime.get_registered_factories()
   print(f"Registered factories: {factories}")
   ```

3. **Message Delivery Issues**
   ```python
   # Check topic health
   from autogen_kafka_extension.shared.topic_admin_service import TopicAdminService
   
   admin = TopicAdminService(config.kafka_config)
   topics = await admin.list_topics()
   print(f"Available topics: {topics}")
   ```

### Performance Tuning

```python
# Optimize for throughput
config = WorkerConfig(
    kafka_config=KafkaConfig(
        # Producer optimization
        batch_size=65536,
        linger_ms=100,
        compression_type="lz4",
        
        # Consumer optimization
        fetch_min_bytes=1024,
        fetch_max_wait_ms=500,
        max_poll_records=1000,
        
        # Memory tuning
        buffer_memory=67108864,  # 64MB
        receive_buffer_bytes=65536,
        send_buffer_bytes=131072,
    )
)
```

### Debugging Tips

```python
# Enable detailed logging
import logging
logging.getLogger("autogen_kafka_extension").setLevel(logging.DEBUG)
logging.getLogger("kstreams").setLevel(logging.DEBUG)

# Monitor message flow
from autogen_kafka_extension.monitoring import MessageFlowMonitor

monitor = MessageFlowMonitor(runtime)
await monitor.start()
```

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please see the main project [README](../README.md) for contribution guidelines.

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd autogen-kafka/python

# Install development dependencies
uv sync --all-extras

# Install pre-commit hooks
pre-commit install

# Run tests
./packages/autogen-kafka-extension/run_tests.sh
```

---

## 🆘 Support

- **Documentation**: This README and the main project [README](../README.md)
- **Issues**: Report bugs and feature requests via GitHub Issues
- **AutoGen Resources**: [Microsoft AutoGen Documentation](https://github.com/microsoft/autogen)
- **Kafka Resources**: [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- **Python Kafka**: [confluent-kafka-python](https://docs.confluent.io/kafka-clients/python/current/overview.html)
- **kstreams**: [kstreams Documentation](https://kstreams.readthedocs.io/)
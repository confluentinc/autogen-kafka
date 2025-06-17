# AutoGen Kafka Extension - Python Implementation

A scalable, event-driven Python runtime for autonomous agents powered by Apache Kafka. The `KafkaWorkerAgentRuntime` extends AutoGen's core `AgentRuntime` to enable message-based communication over Kafka topics, with built-in support for pub/sub and RPC-style patterns.

---

## 📌 Features

- **Agent Lifecycle Management** – Dynamically register agent factories and instances
- **Kafka Message Routing** – Built-in pub/sub and RPC using Kafka topics
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
from autogen_kafka_extension.worker_config import WorkerConfig
from autogen_kafka_extension.worker_runtime import KafkaWorkerAgentRuntime

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
from autogen_kafka_extension.worker_config import KafkaConfig

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
- **`StreamingService`**: Kafka stream processing using kstreams
- **`MessageProcessor`**: Handles message routing and processing logic
- **`AgentRegistry`**: Manages agent factory and instance registration
- **`BackgroundTaskManager`**: Robust background task management
- **`MessageSerDes`**: CloudEvents-based message serialization

### Code Structure

```
src/autogen_kafka_extension/
├── worker_runtime.py           # Main runtime implementation
├── worker_config.py            # Configuration classes
├── streaming_service.py        # Kafka streaming service
├── message_processor.py        # Message processing logic
├── messaging_client.py         # Kafka messaging client
├── agent_registry.py           # Agent registration management
├── agent_manager.py            # Agent lifecycle management
├── subscription_service.py     # Subscription management
├── topic_admin.py              # Kafka topic administration
├── background_task_manager.py  # Background task handling
├── constants.py                # Shared constants
└── events/                     # Event handling and serialization
    ├── message_serdes.py       # Message serialization/deserialization
    ├── request_event.py        # Request event structures
    ├── response_event.py       # Response event structures
    ├── subscription_event.py   # Subscription events
    └── registration_event.py   # Registration events
```

### Debugging and Monitoring

- **OpenTelemetry Integration**: Built-in tracing for message flow visibility
- **Structured Logging**: Comprehensive logging throughout the runtime lifecycle  
- **Error Handling**: Graceful error recovery with detailed error reporting
- **Health Checks**: Runtime health monitoring and diagnostics

### Custom Extensions

#### Custom Message Serialization

```python
from autogen_kafka_extension.events.message_serdes import MessageSerDes

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
from autogen_kafka_extension.message_processor import MessageProcessor

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

### In Progress
- [ ] Enhanced agent state persistence mechanisms
- [ ] Performance optimizations for high-throughput scenarios
- [ ] Advanced CLI tools for monitoring and debugging

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
   from autogen_kafka_extension.topic_admin import TopicAdmin
   
   admin = TopicAdmin(config.kafka_config)
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
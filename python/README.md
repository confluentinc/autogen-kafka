# AutoGen Kafka Extension - Python

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)

A Python extension for [Microsoft AutoGen](https://github.com/microsoft/autogen) that enables distributed agent communication through Apache Kafka. This package provides Kafka-based implementations of agent runtimes and memory systems for building scalable, event-driven multi-agent systems.

## 🚀 Features

- **Distributed Agent Runtime**: Kafka-based agent runtime with horizontal scaling capabilities
- **Streaming Agent Support**: Real-time message processing with Kafka Streams
- **Distributed Memory**: Shared memory implementation across multiple agent instances
- **Event-Driven Architecture**: Asynchronous message processing with CloudEvents support
- **Observability**: Built-in OpenTelemetry tracing and monitoring
- **Fault Tolerance**: Robust error handling and recovery mechanisms
- **Flexible Configuration**: Comprehensive Kafka configuration options with security support

## 📦 Installation

### Using uv (Recommended)

```bash
uv add autogen-kafka-extension
```

### Using pip

```bash
pip install autogen-kafka-extension
```

### Using Poetry

```bash
poetry add autogen-kafka-extension
```

### Using conda/mamba

```bash
# Note: Package may need to be available on conda-forge
conda install -c conda-forge autogen-kafka-extension
# or
mamba install -c conda-forge autogen-kafka-extension
```

### Using pipenv

```bash
pipenv install autogen-kafka-extension
```

### From Source

```bash
git clone https://github.com/microsoft/autogen-kafka.git
cd autogen-kafka/python/packages/autogen-kafka-extension

# Using uv (recommended)
uv pip install -e .

# Using Poetry
poetry install

# Using pip
pip install -e .

# Using pipenv
pipenv install -e .
```

### Development Installation

```bash
git clone https://github.com/microsoft/autogen-kafka.git
cd autogen-kafka/python/packages/autogen-kafka-extension

# Using uv (recommended)
uv pip install -e .[dev]

# Using Poetry
poetry install --with dev

# Using pip
pip install -e .[dev]

# Using pipenv
pipenv install -e .[dev]
```

## 🏗 Architecture

The extension provides three main components for distributed agent communication:

### 1. Agent Runtime (`KafkaWorkerAgentRuntime`)
A distributed agent runtime that enables agents to communicate across multiple processes and machines through Kafka topics.

### 2. Streaming Agent (`KafkaStreamingAgent`) 
A bridge agent that exposes Kafka topics as AutoGen agents, allowing AutoGen agent systems to communicate with external Kafka-based services transparently.

### 3. Distributed Memory (`KafkaMemory`)
A memory implementation that synchronizes state across multiple agent instances using dedicated Kafka topics.

For detailed architecture documentation, see [docs/api/README.md](packages/autogen-kafka-extension/docs/api/README.md).

## 🚀 Quick Start

### 1. Start Kafka Infrastructure

Using Docker Compose (from the repository root):

```bash
docker-compose up -d
```

This starts:
- Apache Kafka broker (localhost:9092)
- Schema Registry (localhost:8081)
- Control Center (localhost:9021)

### 2. Run the Complete Sample Application

The `packages/exemple/` directory contains a complete sample application that demonstrates both Kafka and GRPC runtime usage:

```bash
cd packages/exemple
python main.py
```

**What the sample demonstrates:**
- **Runtime Selection**: Choose between Kafka and GRPC at startup
- **Agent Configuration**: Load configuration from YAML files
- **Interactive Processing**: Input text for sentiment analysis
- **Proper Lifecycle**: Handles startup, processing, and shutdown
- **Error Handling**: Graceful error handling and resource cleanup

**Sample Configuration** (`sample.config.yml`):
```yaml
kafka:
    name: "simple_kafka"
    bootstrap_servers: "localhost:9092"
    group_id: "simple_group_abc"
    client_id: "simple_client_abc"
    
agent:
    request_topic: "simple_request_topic"
    response_topic: "simple_response_topic"
    
runtime:
    runtime_requests: "runtime_requests"
    runtime_responses: "runtime_responses"
    registry_topic: "agent_registry"
    subscription_topic: "agent_subscription"
    publish_topic: "publish"
```

**Sample Application Structure:**
```
packages/exemple/
├── main.py                # Main application entry point
├── sample.py              # Base Sample class (abstract)
├── kafka_sample.py        # Kafka runtime implementation
├── grpcs_sample.py        # GRPC runtime implementation
├── events.py              # Message type definitions
└── sample.config.yml      # Configuration file
```

**Key Features:**
- **Flexible Runtime**: Switch between Kafka and GRPC without code changes
- **Type-Safe Messages**: Define request/response types with JSON schema
- **Configuration Management**: External YAML configuration with validation
- **Interactive Interface**: Command-line interface for testing
- **Proper Shutdown**: Graceful shutdown handling with resource cleanup

### 3. Basic Agent Runtime Setup

```python
import asyncio
from autogen_kafka_extension.runtimes.kafka_agent_runtime import KafkaWorkerAgentRuntime
from autogen_kafka_extension.runtimes.worker_config import WorkerConfig
from autogen_core import BaseAgent, MessageContext

# Configure the runtime
config = WorkerConfig(
    name="my-worker",
    group_id="agent-group",
    client_id="agent-client-1",
    bootstrap_servers=["localhost:9092"],
    request_topic="agent-requests",
    response_topic="agent-responses"
)


# Create a simple agent
class EchoAgent(BaseAgent):
    def __init__(self):
        super().__init__("Echo Agent")

    async def on_message_impl(self, message: str, ctx: MessageContext) -> str:
        return f"Echo: {message}"


async def main():
    # Create and start the runtime
    runtime = KafkaWorkerAgentRuntime(config)

    # Register agent factory
    await runtime.register_factory("echo_agent", EchoAgent)

    # Start the runtime
    await runtime.start()

    try:
        # Runtime processes messages until stopped
        await asyncio.Event().wait()
    finally:
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Kafka Bridge Agent Example

```python
import asyncio
from autogen_kafka_extension.agent.kafka_streaming_agent import KafkaStreamingAgent
from autogen_kafka_extension.agent.kafka_agent_config import KafkaAgentConfig
from autogen_kafka_extension.runtimes.kafka_agent_runtime import KafkaWorkerAgentRuntime
from autogen_kafka_extension.runtimes.worker_config import WorkerConfig
from autogen_core import BaseAgent, MessageContext, AgentId

# Configure the runtime
runtime_config = WorkerConfig(
    name="my-worker",
    group_id="agent-group",
    client_id="agent-client-1",
    bootstrap_servers=["localhost:9092"],
    request_topic="agent-requests",
    response_topic="agent-responses"
)

# Configure the Kafka bridge agent to connect to external Kafka service
kafka_bridge_config = KafkaAgentConfig(
    name="external-service-bridge",
    group_id="bridge-group",
    client_id="bridge-client",
    bootstrap_servers=["localhost:9092"],
    request_topic="external-service-requests",  # Topic to send requests to external service
    response_topic="external-service-responses"  # Topic to receive responses from external service
)


# Example AutoGen agent that will use the Kafka bridge
class DataProcessor(BaseAgent):
    def __init__(self):
        super().__init__("Data Processor")

    async def on_message_impl(self, message: str, ctx: MessageContext) -> str:
        # This agent can now communicate with external Kafka services
        # through the bridge agent as if it were a regular AutoGen agent

        # Send request to external service via Kafka bridge
        external_request = {
            "data": message,
            "operation": "process",
            "timestamp": "2024-01-01T00:00:00Z"
        }

        # The bridge agent will serialize this message, send it to Kafka,
        # wait for the response, and return it as if it were a direct agent call
        response = await self.send_message(external_request, AgentId("kafka_bridge", "default"))

        return f"Processed via external service: {response}"


async def main():
    # Create the runtime
    runtime = KafkaWorkerAgentRuntime(runtime_config)

    # Register regular AutoGen agents
    await runtime.register_factory("data_processor", DataProcessor)

    # Register the Kafka bridge agent - it's treated like any other agent
    kafka_bridge = KafkaStreamingAgent(kafka_bridge_config, "External Service Bridge")
    await runtime.register_agent_instance(kafka_bridge, AgentId("kafka_bridge", "default"))

    # Start the runtime
    await runtime.start()

    try:
        # Now AutoGen agents can communicate with external Kafka services
        # through the registered bridge agent transparently
        print("Runtime started with Kafka bridge agent registered")
        print(f"Bridge connects to topics: {kafka_bridge_config.request_topic} -> {kafka_bridge_config.response_topic}")

        # Runtime processes messages until stopped
        await asyncio.Event().wait()
    finally:
        await runtime.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

### 5. Distributed Memory Usage

```python
import asyncio
from autogen_kafka_extension.memory.kafka_memory import KafkaMemory
from autogen_kafka_extension.memory.memory_config import MemoryConfig
from autogen_core.memory import MemoryContent

# Configure distributed memory
config = MemoryConfig(
    name="shared-memory",
    group_id="memory-group",
    client_id="memory-client",
    bootstrap_servers=["localhost:9092"],
    memory_topic="shared-memory-topic"
)

async def main():
    session_id = "agent-session-1"
    
    # Create distributed memory instance
    async with KafkaMemory(config, session_id) as memory:
        # Add content to shared memory
        content = MemoryContent(
            content="Important information to share",
            metadata={"type": "knowledge", "priority": "high"}
        )
        
        await memory.add(content)
        
        # Query the memory
        results = await memory.query("important information")
        print(f"Found {len(results.memories)} matching memories")
        
        # Memory state is automatically synchronized across instances

if __name__ == "__main__":
    asyncio.run(main())
```

## ⚙️ Configuration

### WorkerConfig

Core configuration for the agent runtime:

```python
from autogen_kafka_extension.runtimes.worker_config import WorkerConfig
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

config = WorkerConfig(
    name="my-worker",
    group_id="agent-group",
    client_id="agent-client-1",
    bootstrap_servers=["localhost:9092"],
    request_topic="agent-requests",
    response_topic="agent-responses",
    
    # Optional Kafka settings
    num_partitions=3,
    replication_factor=1,
    auto_offset_reset="latest",
    
    # Security configuration (optional)
    security_protocol=SecurityProtocol.SASL_SSL,
    security_mechanism=SaslMechanism.PLAIN,
    sasl_plain_username="your-username",
    sasl_plain_password="your-password"
)
```

### KafkaAgentConfig

Configuration for streaming agents:

```python
from autogen_kafka_extension.agent.kafka_agent_config import KafkaAgentConfig

config = KafkaAgentConfig(
    name="streaming-agent",
    group_id="streaming-group",
    client_id="streaming-client", 
    bootstrap_servers=["localhost:9092"],
    request_topic="agent-input",
    response_topic="agent-output"
)
```

### MemoryConfig

Configuration for distributed memory:

```python
from autogen_kafka_extension.memory.memory_config import MemoryConfig

config = MemoryConfig(
    name="distributed-memory",
    group_id="memory-group",
    client_id="memory-client",
    bootstrap_servers=["localhost:9092"],
    memory_topic="shared-memory"
)
```

## 🔍 Key Components

### Agent Runtime Services

- **AgentRegistry**: Manages agent discovery and registration across the cluster
- **SubscriptionService**: Handles topic subscriptions and message routing  
- **MessagingClient**: Provides high-level messaging APIs for agents
- **MessageProcessor**: Processes incoming messages and routes them to agents
- **AgentManager**: Manages local agent instances and their lifecycle

### Event System

The extension uses CloudEvents-compatible event schemas:

- **RequestEvent**: Agent request messages
- **ResponseEvent**: Agent response messages  
- **RegistrationEvent**: Agent registration notifications
- **SubscriptionEvent**: Topic subscription updates
- **MemoryEvent**: Memory synchronization events

### Streaming Infrastructure  

- **StreamingService**: Core Kafka streaming service management
- **StreamingWorkerBase**: Base class for streaming components
- **TopicAdminService**: Kafka topic administration and management
- **BackgroundTaskManager**: Async task coordination

## 🧪 Testing

Run the test suite:

```bash
# Run all tests (as configured in the project)
PYTHONPATH=tests:src uv run python -m pytest tests/test_agent_runtime.py tests/test_kafka_memory.py tests/test_kafka_streaming_agent.py -v

# Or using the provided shell script
./run_tests.sh

# Run individual test files
PYTHONPATH=tests:src uv run python -m pytest tests/test_kafka_streaming_agent.py -v
PYTHONPATH=tests:src uv run python -m pytest tests/test_kafka_memory.py -v
PYTHONPATH=tests:src uv run python -m pytest tests/test_agent_runtime.py -v

# Run with coverage
PYTHONPATH=tests:src uv run python -m pytest tests/ --cov=autogen_kafka_extension -v

# Alternative: Using regular pytest (if you have dependencies installed)
pytest tests/ -v
```

### Test Requirements

Tests use testcontainers for integration testing with real Kafka instances:

```python
# Example test setup
import pytest
from testcontainers.kafka import KafkaContainer

@pytest.fixture(scope="session")
def kafka_container():
    with KafkaContainer() as kafka:
        yield kafka
```

## 🔧 Development

### Project Structure

```
src/autogen_kafka_extension/
├── agent/                      # Streaming agent implementations
│   ├── event/                  # Agent event definitions
│   ├── kafka_agent_config.py   # Agent configuration
│   └── kafka_streaming_agent.py # Main streaming agent
├── memory/                     # Distributed memory system
│   ├── kafka_memory.py         # Kafka-based memory implementation
│   └── memory_config.py        # Memory configuration
├── runtimes/                   # Agent runtime implementations
│   ├── services/               # Runtime service components
│   ├── worker_runtime.py       # Main Kafka worker runtime
│   └── worker_config.py        # Worker configuration
└── shared/                     # Shared utilities and base classes
    ├── events/                 # Event definitions and serialization
    ├── kafka_config.py         # Base Kafka configuration
    ├── streaming_service.py    # Kafka streaming service
    └── streaming_worker_base.py # Base streaming worker
```

### Dependencies

Key dependencies and their purposes:

```toml
[project.dependencies]
autogen = ">=0.6.1"              # Core AutoGen framework
autogen-core = ">=0.6.1"         # AutoGen core components  
kstreams = ">=0.26.9"            # Kafka Streams for Python
confluent-kafka = ">=2.10.1"     # Kafka client library
cloudevents = ">=1.12.0"         # CloudEvents support
```

### Building and Publishing

```bash
# Build the package
uv build

# Install in development mode
uv pip install -e .

# Run tests
PYTHONPATH=tests:src uv run python -m pytest tests/ -v

# Type checking
uv run mypy src/
```

## 🔒 Security Considerations

### Authentication

The extension supports various Kafka authentication mechanisms:

```python
# SASL/PLAIN authentication
config = WorkerConfig(
    # ... other config
    security_protocol=SecurityProtocol.SASL_PLAINTEXT,
    security_mechanism=SaslMechanism.PLAIN,
    sasl_plain_username="username",
    sasl_plain_password="password"
)

# SSL encryption
config = WorkerConfig(
    # ... other config  
    security_protocol=SecurityProtocol.SSL,
    # SSL context is automatically created
)
```

### Topic Security

- Use ACLs to restrict topic access
- Implement proper authentication for all components
- Consider encryption in transit and at rest
- Regular security audits of Kafka infrastructure

## 📊 Monitoring and Observability

### OpenTelemetry Integration

The extension includes built-in tracing support:

```python
from opentelemetry.trace import TracerProvider

# Configure tracing
tracer_provider = TracerProvider()

# Pass to runtime
runtime = KafkaWorkerAgentRuntime(
    config=config,
    tracer_provider=tracer_provider
)
```

### Metrics

Monitor key performance indicators:

- Message processing latency
- Agent registration/deregistration events
- Memory synchronization lag
- Topic partition lag
- Error rates and exception counts

### Logging

Configure structured logging:

```python
import logging

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# The extension uses loggers for different components:
# - autogen_kafka_extension.runtimes.worker_runtime
# - autogen_kafka_extension.agent.kafka_streaming_agent  
# - autogen_kafka_extension.memory.kafka_memory
```

## 🐛 Troubleshooting

### Common Issues

**Connection Errors**
```
Error: Failed to connect to Kafka broker
```
- Verify Kafka is running and accessible
- Check bootstrap_servers configuration
- Verify network connectivity and firewall rules

**Serialization Errors**
```  
Error: Failed to serialize message
```
- Ensure message types are properly registered
- Check CloudEvents compatibility
- Verify JSON serialization support

**Memory Synchronization Issues**
```
Error: Memory event not received
```
- Check topic creation and permissions
- Verify consumer group configuration
- Monitor Kafka topic lag

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging

# Enable debug logging
logging.getLogger('autogen_kafka_extension').setLevel(logging.DEBUG)
logging.getLogger('kstreams').setLevel(logging.DEBUG)
```

## 🤝 Contributing

Contributions are welcome! Please see the main repository's contributing guidelines.

### Development Setup

1. Clone the repository
2. Install development dependencies: `uv pip install -e .[dev]`
3. Run tests: `PYTHONPATH=tests:src uv run python -m pytest tests/ -v`
4. Check code quality: `uv run mypy src/` and `uv run ruff check src/`

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Ensure all tests pass
5. Submit pull request with clear description

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../../../LICENSE) file for details.

## 🔗 Related Projects

- [Microsoft AutoGen](https://github.com/microsoft/autogen) - Multi-agent conversation framework
- [Apache Kafka](https://kafka.apache.org/) - Distributed streaming platform
- [KStreams](https://github.com/kpn/kstreams) - Kafka Streams for Python
- [CloudEvents](https://cloudevents.io/) - Event specification for cloud-native applications 
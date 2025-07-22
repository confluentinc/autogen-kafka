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

### 1. Agent Runtime (`KafkaAgentRuntime`)
A distributed agent runtime that enables agents to communicate across multiple processes and machines through Kafka topics.

### 2. Streaming Agent (`KafkaStreamingAgent`) 
A bridge agent that exposes Kafka topics as AutoGen agents, allowing AutoGen agent systems to communicate with external Kafka-based services transparently. **Note:** The API now requires explicit `request_type` and `response_type` parameters for type safety.

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

The `packages/exemple/autogen-kafka-extension-sample/` directory contains a complete sample application that demonstrates a **distributed sentiment analysis system** using:
- **AutoGen Kafka Extension** for distributed agent communication
- **Kafka** for message streaming between agents
- **File-based Configuration** using YAML configuration files
- **Multiple Agent Runtimes** coordinating across different processes

```bash
cd packages/exemple/autogen-kafka-extension-sample/src
python main.py
```

**What the sample demonstrates:**
- **Multi-Runtime Architecture**: Creates separate Flink and Forwarding runtimes
- **File-based Configuration**: Loads configuration from YAML files using `KafkaAgentRuntimeFactory`
- **Agent Communication**: Distributed agents communicate via Kafka topics
- **Message Type Safety**: Uses strongly-typed `SentimentRequest` and `SentimentResponse` messages
- **Interactive Processing**: Command-line interface for sentiment analysis
- **Proper Lifecycle**: Handles runtime startup, agent registration, and shutdown

**Sample Configuration** (`config_worker1.yml`):
```yaml
kafka:
    name: "simple_kafka"
    bootstrap_servers: "your-cluster.region.provider.confluent.cloud:9092"
    group_id: "your-consumer-group"
    client_id: "your-client-id"
    sasl_plain_username: "YOUR_CONFLUENT_CLOUD_API_KEY"
    sasl_plain_password: "YOUR_CONFLUENT_CLOUD_API_SECRET"
    security_protocol: "SASL_SSL"
    sasl_mechanism: "PLAIN"
    schema_registry:
        url: "https://your-schema-registry.region.provider.confluent.cloud"
        api_key: "YOUR_SCHEMA_REGISTRY_API_KEY"
        api_secret: "YOUR_SCHEMA_REGISTRY_API_SECRET"
    
agent:
    request_topic: "agent_request_topic"
    response_topic: "agent_response_topic"
    
runtime:
    runtime_requests: "runtime_requests"
    runtime_responses: "runtime_responses"
    registry_topic: "agent_registry"
    subscription_topic: "agent_subscription"
    publish_topic: "publish"
```

**Sample Application Structure:**
```
packages/exemple/autogen-kafka-extension-sample/
├── src/
│   ├── main.py                # Main application entry point
│   ├── config_worker1.yml     # Configuration for Flink runtime
│   ├── config_worker2.yml     # Configuration for Forwarding runtime
│   ├── agent_config.yml       # Additional agent configuration
│   ├── flink.sql              # Flink SQL job definition
│   ├── modules/               # Agent implementations and message types
│   │   ├── events.py          # SentimentRequest/Response definitions
│   │   └── forwarding_agent.py # Agent implementation
│   └── README.md              # Sample-specific documentation
└── pyproject.toml             # Package configuration
```

**Key Features:**
- **Factory Pattern**: Uses `KafkaAgentRuntimeFactory.create_runtime_from_file()` for configuration
- **Multi-Process Coordination**: Multiple runtimes communicate via Kafka
- **Type-Safe Messages**: `SentimentRequest`/`SentimentResponse` with JSON schema validation
- **YAML Configuration**: External configuration files with placeholder credentials
- **Agent Registration**: Demonstrates factory-based and instance-based agent registration

### 3. Basic Agent Runtime Setup

#### File-based Configuration (Recommended)

```python
import asyncio
from autogen_kafka_extension import KafkaAgentRuntimeFactory
from autogen_core import BaseAgent, MessageContext

# Create a simple agent
class EchoAgent(BaseAgent):
    def __init__(self):
        super().__init__("Echo Agent")

    async def on_message_impl(self, message: str, ctx: MessageContext) -> str:
        return f"Echo: {message}"

async def main():
    # Create runtime from configuration file
    runtime = await KafkaAgentRuntimeFactory.create_runtime_from_file("config.yml")

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

**Configuration File** (`config.yml`):
```yaml
kafka:
    name: "my-worker"
    bootstrap_servers: "localhost:9092"
    group_id: "agent-group"
    client_id: "agent-client-1"
    schema_registry:
        url: "http://localhost:8081"

runtime:
    runtime_requests: "agent-requests"
    runtime_responses: "agent-responses" 
    registry_topic: "agent-registry"
    subscription_topic: "agent-subscription"
    publish_topic: "publish"
```

#### Programmatic Configuration

```python
import asyncio
from autogen_kafka_extension import KafkaAgentRuntime, KafkaAgentRuntimeConfig, KafkaConfig, SchemaRegistryConfig
from autogen_core import BaseAgent, MessageContext

# Configure the runtime
schema_registry_config = SchemaRegistryConfig(
    url="http://localhost:8081"
)

kafka_config = KafkaConfig(
    name="my-worker",
    group_id="agent-group", 
    client_id="agent-client-1",
    bootstrap_servers=["localhost:9092"],
    schema_registry_config=schema_registry_config
)

config = KafkaAgentRuntimeConfig(
    kafka_config=kafka_config,
    request_topic="agent-requests",
    response_topic="agent-responses",
    registry_topic="agent-registry",
    subscription_topic="agent-subscription",
    publish_topic="publish"
)

# Create a simple agent
class EchoAgent(BaseAgent):
    def __init__(self):
        super().__init__("Echo Agent")

    async def on_message_impl(self, message: str, ctx: MessageContext) -> str:
        return f"Echo: {message}"

async def main():
    # Create and start the runtime
    runtime = KafkaAgentRuntime(config)

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
from autogen_kafka_extension import (
    KafkaStreamingAgent, KafkaAgentConfig, KafkaAgentRuntime, 
    KafkaAgentRuntimeConfig, KafkaConfig, SchemaRegistryConfig
)
from autogen_kafka_extension.agent.kafka_message_type import KafkaMessageType
from autogen_core import BaseAgent, MessageContext, AgentId
from dataclasses import dataclass

# Define message types for the bridge agent
@dataclass
class SentimentRequest(KafkaMessageType):
    text: str

@dataclass  
class SentimentResponse(KafkaMessageType):
    sentiment: str

# Configure the runtime
schema_registry_config = SchemaRegistryConfig(
    url="http://localhost:8081"
)

kafka_config = KafkaConfig(
    name="my-worker",
    group_id="agent-group",
    client_id="agent-client-1",
    bootstrap_servers=["localhost:9092"],
    schema_registry_config=schema_registry_config
)

runtime_config = KafkaAgentRuntimeConfig(
    kafka_config=kafka_config,
    request_topic="agent-requests",
    response_topic="agent-responses",
    registry_topic="agent-registry",
    subscription_topic="agent-subscription",
    publish_topic="publish"
)

# Configure the Kafka bridge agent to connect to external Kafka service
bridge_kafka_config = KafkaConfig(
    name="external-service-bridge",
    group_id="bridge-group",
    client_id="bridge-client",
    bootstrap_servers=["localhost:9092"],
    schema_registry_config=schema_registry_config
)

kafka_bridge_config = KafkaAgentConfig(
    kafka_config=bridge_kafka_config,
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
    runtime = KafkaAgentRuntime(runtime_config)

    # Register regular AutoGen agents
    await runtime.register_factory("data_processor", DataProcessor)

    # Register the Kafka bridge agent - it's treated like any other agent
    kafka_bridge = KafkaStreamingAgent(
        config=kafka_bridge_config,
        description="External Service Bridge",
        request_type=SentimentRequest,
        response_type=SentimentResponse,
    )
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

### 5. KafkaStreamingAgent API Changes

**Important:** The `KafkaStreamingAgent` constructor now requires explicit type parameters:

```python
from autogen_kafka_extension import KafkaStreamingAgent, KafkaAgentConfig, KafkaConfig, SchemaRegistryConfig
from autogen_kafka_extension.agent.kafka_message_type import KafkaMessageType
from dataclasses import dataclass

# Define your message types
@dataclass
class MyRequest(KafkaMessageType):
    text: str

@dataclass
class MyResponse(KafkaMessageType):
    result: str

# Configure the agent
schema_registry_config = SchemaRegistryConfig(url="http://localhost:8081")
kafka_config = KafkaConfig(
    name="my-streaming-agent",
    group_id="streaming-group",
    client_id="streaming-client",
    bootstrap_servers=["localhost:9092"],
    schema_registry_config=schema_registry_config
)
config = KafkaAgentConfig(
    kafka_config=kafka_config,
    request_topic="my-requests",
    response_topic="my-responses"
)

# Create agent with required type parameters
agent = KafkaStreamingAgent(
    config=config,
    description="My agent description",
    request_type=MyRequest,      # Required
    response_type=MyResponse,    # Required
)
```

**Breaking Change:** The old constructor `KafkaStreamingAgent(config, description)` is no longer supported. Both `request_type` and `response_type` are now required parameters.

### 6. Distributed Memory Usage

```python
import asyncio
from autogen_kafka_extension import KafkaMemory, KafkaMemoryConfig, KafkaConfig, SchemaRegistryConfig
from autogen_core.memory import MemoryContent

# Configure distributed memory
schema_registry_config = SchemaRegistryConfig(url="http://localhost:8081")
kafka_config = KafkaConfig(
    name="shared-memory",
    group_id="memory-group", 
    client_id="memory-client",
    bootstrap_servers=["localhost:9092"],
    schema_registry_config=schema_registry_config
)

config = KafkaMemoryConfig(
    kafka_config=kafka_config,
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

### KafkaAgentRuntimeConfig

Core configuration for the agent runtime:

```python
from autogen_kafka_extension import KafkaAgentRuntimeConfig, KafkaConfig, SchemaRegistryConfig
from kstreams.backends.kafka import SecurityProtocol, SaslMechanism

# Schema Registry configuration
schema_registry_config = SchemaRegistryConfig(
    url="http://localhost:8081",
    api_key="your-api-key",
    api_secret="your-api-secret"
)

# Core Kafka configuration
kafka_config = KafkaConfig(
    name="my-worker",
    group_id="agent-group",
    client_id="agent-client-1", 
    bootstrap_servers=["localhost:9092"],
    schema_registry_config=schema_registry_config,
    
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

# Agent runtime configuration
config = KafkaAgentRuntimeConfig(
    kafka_config=kafka_config,
    request_topic="agent-requests",
    response_topic="agent-responses", 
    registry_topic="agent-registry",
    subscription_topic="agent-subscription",
    publish_topic="publish"
)
```

### KafkaAgentConfig

Configuration for streaming agents:

```python
from autogen_kafka_extension import KafkaAgentConfig, KafkaConfig, SchemaRegistryConfig

# Schema Registry configuration
schema_registry_config = SchemaRegistryConfig(url="http://localhost:8081")

# Kafka configuration
kafka_config = KafkaConfig(
    name="streaming-agent",
    group_id="streaming-group",
    client_id="streaming-client",
    bootstrap_servers=["localhost:9092"],
    schema_registry_config=schema_registry_config
)

# Agent configuration
config = KafkaAgentConfig(
    kafka_config=kafka_config,
    request_topic="agent-input",
    response_topic="agent-output"
)
```

### KafkaMemoryConfig

Configuration for distributed memory:

```python
from autogen_kafka_extension import KafkaMemoryConfig, KafkaConfig, SchemaRegistryConfig

# Schema Registry configuration  
schema_registry_config = SchemaRegistryConfig(url="http://localhost:8081")

# Kafka configuration
kafka_config = KafkaConfig(
    name="distributed-memory",
    group_id="memory-group",
    client_id="memory-client", 
    bootstrap_servers=["localhost:9092"],
    schema_registry_config=schema_registry_config
)

# Memory configuration
config = KafkaMemoryConfig(
    kafka_config=kafka_config,
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
# Navigate to the extension directory
cd packages/autogen-kafka-extension

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
# Navigate to the extension directory
cd packages/autogen-kafka-extension

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
# - autogen_kafka_extension.runtimes.kafka_agent_runtime
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
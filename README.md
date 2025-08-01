# Autogen Kafka Extension

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A scalable, event-driven runtime extension for [Microsoft AutoGen](https://github.com/microsoft/autogen) that enables autonomous agents to communicate over Apache Kafka. This extension provides distributed agent communication capabilities supporting message-based patterns including pub/sub and RPC-style interactions across multiple programming languages.

## 🚀 Key Features

- **Event-Driven Architecture**: Built on Apache Kafka for scalable, distributed agent communication
- **Multi-Language Support**: Extensible architecture supporting multiple programming languages
- **Agent Lifecycle Management**: Dynamic registration and management of agent factories and instances
- **Multiple Communication Patterns**: Support for both pub/sub and RPC-style messaging
- **Distributed Memory**: Kafka-based memory implementation for sharing state across agent instances
- **Streaming Processing**: Asynchronous event processing for high-throughput scenarios
- **Schema Support**: Standardized message serialization with CloudEvents support
- **Observability**: Integrated tracing and monitoring capabilities
- **Fault Tolerance**: Robust error handling and recovery mechanisms

## 🏗 Architecture Overview

The Autogen Kafka Extension implements a distributed agent runtime that leverages Apache Kafka's streaming capabilities to enable:

- **Horizontal Scaling**: Agents can be distributed across multiple instances and locations
- **Loose Coupling**: Agents communicate through well-defined message contracts
- **Event Sourcing**: All interactions are captured as immutable events
- **Resilience**: Built-in fault tolerance and recovery mechanisms
- **Language Agnostic**: Core patterns can be implemented across different programming languages

## 📦 Project Structure

```
autogen-kafka/
├── .github/                             # GitHub workflows and settings
├── python/                              # Python implementation
│   ├── packages/
│   │   └── autogen-kafka-extension/     # Core Python extension package
│   │       ├── src/
│   │       │   └── autogen_kafka_extension/
│   │       │       ├── agent/                       # Agent implementations
│   │       │       │   ├── kafka_streaming_agent.py # Direct Kafka streaming agent
│   │       │       │   ├── kafka_agent_config.py   # Agent configuration classes
│   │       │       │   └── event/                  # Agent event definitions
│   │       │       │       ├── agent_event.py      # Core agent event structure
│   │       │       │       └── agent_event_serdes.py # Event serialization
│   │       │       ├── memory/                      # Distributed memory implementation
│   │       │       │   ├── kafka_memory.py         # Kafka-based memory provider
│   │       │       │   └── memory_config.py        # Memory configuration
│   │       │       ├── runtimes/                   # Agent runtime implementations
│   │       │       │   ├── worker_runtime.py       # Main Kafka worker runtime
│   │       │       │   ├── worker_config.py        # Worker configuration classes
│   │       │       │   ├── messaging_client.py     # Kafka messaging client
│   │       │       │   └── services/               # Runtime service components
│   │       │       │       ├── agent_manager.py    # Agent lifecycle management
│   │       │       │       ├── agent_registry.py   # Agent registration management
│   │       │       │       ├── message_processor.py # Message processing logic
│   │       │       │       └── subscription_service.py # Subscription management
│   │       │       ├── shared/                     # Shared components and utilities
│   │       │       │   ├── events/                 # Event definitions and serialization
│   │       │       │   │   ├── memory_event.py     # Memory synchronization events
│   │       │       │   │   ├── request_event.py    # Agent request events
│   │       │       │   │   ├── response_event.py   # Agent response events
│   │       │       │   │   ├── registration_event.py # Agent registration events
│   │       │       │   │   └── subscription_event.py # Subscription events
│   │       │       │   ├── kafka_config.py         # Base Kafka configuration
│   │       │       │   ├── streaming_service.py    # Kafka streaming service
│   │       │       │   ├── streaming_worker_base.py # Base streaming worker class
│   │       │       │   └── topic_admin_service.py  # Topic administration
│   │       │       └── py.typed                    # Type hints marker
│   │       ├── tests/                   # Package tests
│   │       │   ├── test_kafka_memory.py # Memory implementation tests
│   │       │   ├── test_worker_runtime.py # Runtime tests
│   │       │   └── utils.py            # Test utilities
│   │       └── pyproject.toml          # Package configuration
│   └── README.md                       # Python-specific implementation guide
├── dotnet/                             # Future C# implementation
├── docs/                               # Architecture and design documentation
├── examples/                           # Cross-language usage examples
├── docker-compose.yml                  # Kafka development environment
├── service.yml                         # Service configuration
├── CHANGELOG.md                        # Version history
├── LICENSE                             # Apache 2.0 License
└── README.md                          # This file
```

## 🌍 Language Support

### Current Implementations

- **Python** (`python/`): Full-featured implementation with comprehensive agent runtime
  - AutoGen integration via `KafkaWorkerAgentRuntime`
  - Direct agent communication with `KafkaStreamingAgent`
  - Kafka Streams processing with `kstreams`
  - CloudEvents support and OpenTelemetry tracing
  - See [Python README](python/packages/autogen-kafka/README.md) for detailed usage

### Planned Implementations

- **C#** (`dotnet/`): Planned implementation for .NET ecosystems

## 🚀 Core Concepts

### Agent Runtime

The extension provides language-specific implementations of agent runtimes that:
- Register and manage agent lifecycles
- Route messages between agents via Kafka topics
- Handle both synchronous (RPC) and asynchronous (pub/sub) communication patterns
- Provide observability and error handling

### Kafka Streaming Agent

The `KafkaStreamingAgent` provides a direct Kafka-based communication layer for AutoGen agents:
- **Direct Kafka Integration**: Agents communicate directly through Kafka topics without additional runtime layers
- **Request-Response Correlation**: Built-in correlation mechanism for synchronous message patterns
- **Event-Driven Processing**: Asynchronous message handling with Kafka Streams integration
- **Serialization Support**: Automatic message serialization/deserialization with AutoGen's serialization registry
- **Background Task Management**: Non-blocking message sending with background task coordination
- **Configurable Topics**: Separate request and response topics for organized message flow
- **Type-Safe Messages**: Requires explicit request and response type definitions for compile-time safety

### Message Patterns

- **Direct Messaging**: Point-to-point communication between specific agents
- **Topic Broadcasting**: Publish-subscribe patterns for event distribution
- **Request-Response**: RPC-style interactions with response correlation
- **Event Streaming**: Continuous processing of event streams

### Distributed Memory

The extension provides a Kafka-based memory implementation (`KafkaMemory`) that enables:
- **Shared State**: Memory content synchronized across multiple agent instances
- **Session Isolation**: Each memory session uses dedicated Kafka topics for isolation
- **Persistence**: Memory state persisted in Kafka topics for durability
- **Event Synchronization**: Real-time memory updates broadcast to all instances
- **Flexible Backend**: Wraps existing memory implementations (e.g., `ListMemory`)

### Configuration Management

- Environment-specific configurations for Kafka connectivity
- Topic and partition management
- Consumer group and scaling strategies
- Security and authentication settings

## 📋 Requirements

### Infrastructure
- **Apache Kafka**: Version 2.8+ (local cluster or managed service)
- **ZooKeeper**: If using older Kafka versions
- **Container Runtime**: Docker for local development (optional)

### Language-Specific Requirements
- **Python**: 3.10+ with AutoGen Core dependencies
- **C#**: .NET 6+ (planned)

## 🏃 Getting Started

### 1. Infrastructure Setup

**For the included sample application**, set up Confluent Cloud:

1. **Create a Confluent Cloud account** and Kafka cluster
2. **Set up Schema Registry** with API keys
3. **Create required topics** in your cluster
4. **Deploy the Flink SQL job** for the remote sentiment analysis agent

**For local development**, start a local Kafka cluster:

```bash
# Using the provided Docker Compose
docker-compose up -d
```

Or configure connection to your existing Kafka infrastructure.

### 2. Choose Your Implementation

#### Python
Navigate to the Python implementation:

```bash
cd python
```

Follow the [Python README](python/packages/autogen-kafka/README.md) for detailed setup and usage instructions.

#### Other Languages
Additional language implementations are planned. Check the respective directories when available.

### 3. Basic Concepts

All implementations follow these core patterns:

1. **Runtime Configuration**: Configure Kafka connectivity and topics
2. **Agent Registration**: Register agent factories and instances
3. **Message Handling**: Implement agents that process incoming messages
4. **Communication**: Use direct messaging or topic publishing for agent interaction

### 4. Practical Usage Examples

The project includes complete sample applications in `python/packages/exemple/` that demonstrate both Kafka and GRPC runtime usage:

#### Quick Start with Sample Application

```python
# Run the interactive distributed sentiment analysis sample
cd python/packages/exemple
python main.py
```

The sample application demonstrates a **distributed sentiment analysis system**:
- **Local Agent**: Python application using AutoGen Kafka Extension
- **Remote Agent**: Flink SQL job with OpenAI integration
- **Cloud Infrastructure**: Confluent Cloud for messaging
- **Interactive Interface**: Input text for sentiment analysis
- **Runtime Selection**: Choose between Kafka and GRPC at startup

#### Creating Your Own Agent Application

**Step 1: Define Message Types**

```python
from dataclasses import dataclass
from autogen_kafka.agent.kafka_message_type import KafkaMessageType


@dataclass
class SentimentRequest(KafkaMessageType):
  text: str


@dataclass
class SentimentResponse(KafkaMessageType):
  sentiment: str
```

**Step 2: Create Configuration File**

```yaml
kafka:
    name: "my_agent_runtime"
    bootstrap_servers: "localhost:9092"
    group_id: "my_group"
    client_id: "my_client"
    
agent:
    request_topic: "agent_requests"
    response_topic: "agent_responses"
    
runtime:
    runtime_requests: "runtime_requests"
    runtime_responses: "runtime_responses"
    registry_topic: "agent_registry"
    subscription_topic: "agent_subscription"
    publish_topic: "publish"
```

**Step 3: Implement Your Agent Wrapper**

```python
from abc import ABC, abstractmethod
from autogen_kafka import KafkaStreamingAgent, KafkaAgentConfig


class AgentBase(ABC):
  def __init__(self, runtime):
    self._agent_config = KafkaAgentConfig.from_file("config.yml")
    self._runtime = runtime

  def is_running(self) -> bool:
    return self._runtime is not None and self._runtime.is_running()

  async def new_agent(self):
    agent = KafkaStreamingAgent(
      config=self._agent_config,
      description="My custom agent",
      request_type=SentimentRequest,
      response_type=SentimentResponse,
    )
    await agent.start()
    await agent.wait_for_streams_to_start()
    return agent

  async def start(self):
    await self._start()
    # Register serializers and agent factory
    await self._runtime.register_factory("my_agent", self.new_agent)

  async def get_sentiment(self, text: str) -> SentimentResponse:
    response = await self._runtime.send_message(
      message=SentimentRequest(text),
      recipient=AgentId(type="my_agent", key="default")
    )
    return response

  @abstractmethod
  async def _start(self):
    pass

  @abstractmethod
  async def stop(self):
    pass
```

**Step 4: Choose Runtime Implementation**

```python
# Kafka Runtime
from autogen_kafka import KafkaAgentRuntime, KafkaAgentRuntimeConfig


class KafkaAgentApp(AgentBase):
  def __init__(self):
    config = KafkaAgentRuntimeConfig.from_file("config.yml")
    runtime = KafkaAgentRuntime(config=config)
    super().__init__(runtime=runtime)

  async def _start(self):
    await self._runtime.start_and_wait_for()

  async def stop(self):
    if self._runtime:
      await self._runtime.stop()


# GRPC Runtime
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime


class GrpcAgentApp(AgentBase):
  def __init__(self):
    runtime = GrpcWorkerAgentRuntime("localhost:50051")
    super().__init__(runtime=runtime)

  async def _start(self):
    await self._runtime.start()

  async def stop(self):
    await self._runtime.stop()
```

**Step 5: Build Your Application**

```python
import asyncio
import aiorun

class Application:
    def __init__(self):
        self.agent_app = None
    
    async def start(self):
        # Choose runtime
        runtime_choice = input("Select runtime (Kafka/GRPC): ")
        
        if runtime_choice.upper() == "GRPC":
            self.agent_app = GrpcAgentApp()
        else:
            self.agent_app = KafkaAgentApp()
        
        await self.agent_app.start()
        
        # Interactive loop
        while True:
            text = input("Enter text for analysis (or 'exit'): ")
            if text == "exit":
                break
                
            result = await self.agent_app.get_sentiment(text)
            print(f"Result: {result.sentiment}")
        
        await self.agent_app.stop()
    
    async def shutdown(self, loop):
        if self.agent_app and self.agent_app.is_running():
            await self.agent_app.stop()

if __name__ == "__main__":
    app = Application()
    aiorun.run(app.start(), stop_on_unhandled_errors=True, 
               shutdown_callback=app.shutdown)
```

This pattern provides:
- **Flexibility**: Easy switching between different runtimes
- **Scalability**: Horizontal scaling with Kafka runtime
- **Maintainability**: Clear separation of concerns
- **Extensibility**: Easy to add new runtime types or modify behavior

## 🛠 Development

### Contributing

This repository welcomes contributions across all language implementations:

1. **Architecture**: Core patterns and message schemas
2. **Implementation**: Language-specific runtime implementations
3. **Documentation**: Usage guides and architectural decisions
4. **Testing**: Integration and performance testing
5. **Examples**: Cross-language demonstration scenarios

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Implement changes with appropriate tests
4. Ensure compatibility with existing message formats
5. Submit a pull request with clear documentation

### Testing

Each language implementation includes:
- Unit tests for core functionality
- Integration tests with real Kafka clusters
- Performance benchmarks
- Cross-language compatibility tests

## 📊 Monitoring and Observability

The extension provides comprehensive observability:

- **Distributed Tracing**: OpenTelemetry integration for message flow tracking
- **Metrics**: Agent performance and message throughput monitoring
- **Logging**: Structured logging for debugging and audit trails
- **Health Checks**: Runtime and dependency health monitoring

## 🔧 Configuration

### Kafka Topics

The extension uses standardized topic naming conventions:
- `agent.requests` - Direct agent messaging
- `agent.responses` - Response correlation
- `agent.subscription` - Agent subscription events
- `agent.registry` - Agent lifecycle events
- `agent_request` - KafkaStreamingAgent request topic (configurable)
- `agent_response` - KafkaStreamingAgent response topic (configurable)
- `memory.<session_id>` - Distributed memory synchronization (per session)

### Message Formats

All implementations use CloudEvents-compatible message formats for:
- Cross-language compatibility
- Schema evolution support
- Observability integration
- Standard tooling compatibility

## 📈 Roadmap

- [x] Complete Python implementation with full AutoGen integration
- [x] Kafka-based distributed memory implementation
- [ ] Schema registry integration
- [ ] Agent state persistence enhancements
- [ ] Comprehensive documentation and examples
- [ ] C# implementation planning and design
- [ ] C# implementation with .NET AutoGen integration
- [ ] Cross-language message format standardization
- [ ] Advanced observability and monitoring tools
- [ ] Performance optimization and benchmarking

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🤝 Support & Community

- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Join architectural discussions in GitHub Discussions
- **Documentation**: Language-specific guides in respective directories
- **AutoGen Community**: Connect with the broader AutoGen ecosystem
- **Kafka Resources**: [Apache Kafka Documentation](https://kafka.apache.org/documentation/)

## 🔗 Related Projects

- [Microsoft AutoGen](https://github.com/microsoft/autogen) - Core agent framework
- [Apache Kafka](https://kafka.apache.org/) - Distributed streaming platform
- [CloudEvents](https://cloudevents.io/) - Event specification standard
- [OpenTelemetry](https://opentelemetry.io/) - Observability framework

---

**Note**: This is an extension for Microsoft AutoGen. Familiarity with [core AutoGen concepts](https://github.com/microsoft/autogen) is recommended before using this Kafka extension.

# Autogen Kafka Extension

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A scalable, event-driven runtime extension for [Microsoft AutoGen](https://github.com/microsoft/autogen) that enables autonomous agents to communicate over Apache Kafka. This extension provides distributed agent communication capabilities supporting message-based patterns including pub/sub and RPC-style interactions across multiple programming languages.

## 🚀 Key Features

- **Event-Driven Architecture**: Built on Apache Kafka for scalable, distributed agent communication
- **Multi-Language Support**: Extensible architecture supporting multiple programming languages
- **Agent Lifecycle Management**: Dynamic registration and management of agent factories and instances
- **Multiple Communication Patterns**: Support for both pub/sub and RPC-style messaging
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
│   │       │       ├── worker_runtime.py           # Main runtime implementation
│   │       │       ├── worker_config.py            # Configuration classes
│   │       │       ├── streaming_service.py        # Kafka streaming service
│   │       │       ├── message_processor.py        # Message processing logic
│   │       │       ├── messaging_client.py         # Kafka messaging client
│   │       │       ├── agent_registry.py           # Agent registration management
│   │       │       ├── agent_manager.py            # Agent lifecycle management
│   │       │       ├── subscription_service.py     # Subscription management
│   │       │       ├── events/                     # Event handling and serialization
│   │       │       └── ...                         # Additional components
│   │       ├── tests/                   # Package tests
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
  - Kafka Streams processing with `kstreams`
  - CloudEvents support and OpenTelemetry tracing
  - See [Python README](python/README.md) for detailed usage

### Planned Implementations

- **C#** (`dotnet/`): Planned implementation for .NET ecosystems

## 🚀 Core Concepts

### Agent Runtime

The extension provides language-specific implementations of agent runtimes that:
- Register and manage agent lifecycles
- Route messages between agents via Kafka topics
- Handle both synchronous (RPC) and asynchronous (pub/sub) communication patterns
- Provide observability and error handling

### Message Patterns

- **Direct Messaging**: Point-to-point communication between specific agents
- **Topic Broadcasting**: Publish-subscribe patterns for event distribution
- **Request-Response**: RPC-style interactions with response correlation
- **Event Streaming**: Continuous processing of event streams

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

Start a local Kafka cluster for development:

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

Follow the [Python README](python/README.md) for detailed setup and usage instructions.

#### Other Languages
Additional language implementations are planned. Check the respective directories when available.

### 3. Basic Concepts

All implementations follow these core patterns:

1. **Runtime Configuration**: Configure Kafka connectivity and topics
2. **Agent Registration**: Register agent factories and instances
3. **Message Handling**: Implement agents that process incoming messages
4. **Communication**: Use direct messaging or topic publishing for agent interaction

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
- `agent.events` - Event broadcasting
- `agent.registry` - Agent lifecycle events

### Message Formats

All implementations use CloudEvents-compatible message formats for:
- Cross-language compatibility
- Schema evolution support
- Observability integration
- Standard tooling compatibility

## 📈 Roadmap

### Short Term
- [ ] Complete Python implementation with full AutoGen integration
- [ ] C# implementation planning and design
- [ ] Cross-language message format standardization
- [ ] Comprehensive documentation and examples

### Medium Term
- [ ] C# implementation with .NET AutoGen integration
- [ ] Advanced observability and monitoring tools
- [ ] Performance optimization and benchmarking
- [ ] Schema registry integration

### Long Term
- [ ] Additional language implementations (Java, Go)
- [ ] Advanced agent state persistence
- [ ] Multi-cluster and federation support
- [ ] Advanced security and authentication features

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

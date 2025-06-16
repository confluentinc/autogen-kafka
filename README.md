# Autogen Kafka Extension

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

A scalable, event-driven runtime extension for [Microsoft AutoGen](https://github.com/microsoft/autogen) that enables autonomous agents to communicate over Apache Kafka. This extension provides the `KafkaWorkerAgentRuntime` which extends the core `AgentRuntime` to support message-based communication patterns including pub/sub and RPC-style interactions.

## 🚀 Features

- **Event-Driven Architecture**: Built on Apache Kafka for scalable, distributed agent communication
- **Agent Lifecycle Management**: Dynamic registration of agent factories and instances
- **Multiple Communication Patterns**: Support for both pub/sub and RPC-style messaging
- **Streaming Processing**: Powered by `kstreams` for asynchronous event processing
- **Schema Support**: JSON and CloudEvents-based message serialization
- **Observability**: Integrated OpenTelemetry tracing for monitoring and debugging
- **Fault Tolerance**: Robust error handling and background task management

## 📦 Project Structure

```
autogen-kafka/
├── .github/                             # GitHub workflows and settings
│   └── CODEOWNERS                       # Code ownership configuration
├── python/                              # Main Python workspace
│   ├── packages/
│   │   └── autogen-kafka-extension/     # Core extension package
│   │       ├── src/
│   │       │   └── autogen_kafka_extension/
│   │       │       ├── worker_runtime.py           # Main runtime implementation
│   │       │       ├── worker_config.py            # Configuration classes
│   │       │       ├── streaming_service.py        # Kafka streaming service
│   │       │       ├── streaming_worker_base.py    # Base streaming worker
│   │       │       ├── message_processor.py        # Message processing logic
│   │       │       ├── messaging_client.py         # Kafka messaging client
│   │       │       ├── agent_registry.py           # Agent registration management
│   │       │       ├── agent_manager.py            # Agent lifecycle management
│   │       │       ├── subscription_service.py     # Subscription management
│   │       │       ├── topic_admin.py              # Kafka topic administration
│   │       │       ├── background_task_manager.py  # Background task handling
│   │       │       ├── constants.py                # Shared constants
│   │       │       ├── events/                     # Event handling and serialization
│   │       │       │   ├── message_serdes.py       # Message serialization/deserialization
│   │       │       │   ├── request_event.py        # Request event structures
│   │       │       │   ├── response_event.py       # Response event structures
│   │       │       │   ├── subscription_event.py   # Subscription events
│   │       │       │   └── registration_event.py   # Registration events
│   │       │       ├── __init__.py                 # Package initialization
│   │       │       └── py.typed                    # Type hints marker
│   │       ├── tests/                   # Package tests
│   │       │   ├── test_worker_runtime.py
│   │       │   ├── utils.py
│   │       │   └── __init__.py
│   │       ├── run_tests.sh            # Test runner script
│   │       └── pyproject.toml          # Package configuration
│   ├── assets/                         # Project assets (empty)
│   ├── docker-compose.yml              # Kafka development environment
│   ├── pyproject.toml                  # Python workspace configuration
│   ├── uv.lock                         # Dependency lock file
│   ├── shared_tasks.toml               # Shared task configuration
│   ├── LICENSE                         # Apache 2.0 License
│   └── README.md                       # Detailed implementation guide
├── pyproject.toml                       # Root project metadata
├── service.yml                          # Service configuration
├── CHANGELOG.md                         # Version history
├── LICENSE                              # Apache 2.0 License
└── README.md                           # This file
```

## 📋 Requirements

- **Python**: 3.10 or higher
- **Apache Kafka**: Local cluster or managed service (e.g., Confluent Cloud)
- **UV**: For dependency management (recommended)

### Core Dependencies
- `autogen-core>=0.6.1` - Core AutoGen framework
- `autogen>=0.1.0` - AutoGen library
- `confluent-kafka>=2.10.1` - Kafka client
- `kstreams>=0.26.9` - Kafka Streams abstraction
- `cloudevents>=1.12.0` - CloudEvents support
- `aiorun>=2025.1.1` - Async runtime management

### Development Dependencies
- `pytest>=8.4.0` - Testing framework
- `pytest-asyncio>=1.0.0` - Async testing support
- `testcontainers>=4.10.0` - Integration testing with Kafka

## 🏃 Quick Start

### 1. Installation

Navigate to the Python directory and install dependencies using UV:

```bash
cd python
uv sync --all-extras
```

### 2. Kafka Setup

Ensure your Kafka cluster is running. For local development, you can use the provided Docker Compose configuration:

```bash
# Navigate to the python directory and start Kafka
cd python
docker-compose up -d
```

Or use a managed Kafka service like Confluent Cloud.

### 3. Basic Usage

```python
from autogen_kafka_extension.worker_config import WorkerConfig
from autogen_kafka_extension.worker_runtime import KafkaWorkerAgentRuntime
from autogen_core.agent import AgentId

# Configure the runtime
config = WorkerConfig(
    request_topic="agent.requests",
    subscription_topic="agent.responses", 
    group_id="worker-group",
    client_id="worker-client",
    title="My Agent Runtime"
)

# Create and start the runtime
runtime = KafkaWorkerAgentRuntime(config)
await runtime.start()

# Register an agent factory
await runtime.register_factory("echo", lambda: EchoAgent())

# Register a specific agent instance
agent_id = AgentId("echo", "instance-001")
await runtime.register_agent_instance(EchoAgent(), agent_id)

# Send a message (RPC-style)
response = await runtime.send_message(
    "Hello World", 
    recipient=AgentId("echo", "instance-001")
)

# Publish a message (broadcast)
from autogen_core.topic import TopicId
await runtime.publish_message(
    "Announcement", 
    topic_id=TopicId("event", "broadcast")
)
```

## 🛠 Development

### Running Tests

To run the tests, you have several options:

```bash
# From the root directory
cd python/packages/autogen-kafka-extension
./run_tests.sh

# Or manually with proper PYTHONPATH
cd python/packages/autogen-kafka-extension
PYTHONPATH=tests:src uv run python -m pytest tests/test_worker_runtime.py

# Or run all tests from the python workspace
cd python
uv run pytest packages/autogen-kafka-extension/tests/
```

### Development Setup

The project uses:
- **UV** for dependency management and Python tooling
- **pytest** for testing with async support
- **testcontainers** for integration testing with Kafka
- **Workspace structure** for organized package management

### Package Development

The extension is organized as a UV workspace with the main package located in `python/packages/autogen-kafka-extension/`. This structure allows for:
- Clean separation of concerns
- Easy testing and development
- Extensible architecture for additional packages

## 📖 Documentation

For detailed implementation guides, architecture details, and advanced usage examples, see the [Python README](python/README.md).

## 🤝 Contributing

This repository is part of the broader AutoGen ecosystem and welcomes contributions from the community.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with appropriate tests
4. Ensure all tests pass (`uv run pytest`)
5. Submit a pull request

Please ensure your code follows the project's coding standards and includes appropriate tests.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🔄 Changelog

See [CHANGELOG.md](CHANGELOG.md) for details of recent updates and version history.

## 🆘 Support & Resources

- **Issues**: Report bugs and request features via GitHub Issues
- **Documentation**: Check the [Python README](python/README.md) for detailed usage
- **AutoGen Core**: Learn about [AutoGen concepts](https://github.com/microsoft/autogen)
- **Apache Kafka**: [Official Kafka documentation](https://kafka.apache.org/documentation/)
- **Community**: Join discussions in the AutoGen community

## 🎯 Roadmap

- [ ] Enhanced agent state persistence
- [ ] Agent metadata service integration
- [ ] Pluggable metrics and monitoring
- [ ] Advanced CLI tooling for debugging
- [ ] Extended CloudEvents support
- [ ] Performance optimizations for high-throughput scenarios

---

**Note**: This is an extension for Microsoft AutoGen. Familiarity with [core AutoGen concepts](https://github.com/microsoft/autogen) is recommended before using this Kafka extension.

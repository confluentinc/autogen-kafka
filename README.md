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
├── python/                    # Main Python workspace
│   ├── packages/
│   │   └── autogen-kafka-extension/  # Core extension package
│   │       └── src/
│   │           └── autogen_kafka_extension/
│   │               ├── worker_runtime.py      # Main runtime implementation
│   │               ├── worker_config.py       # Configuration classes
│   │               ├── _streaming.py          # Kafka streaming logic
│   │               ├── _message_serdes.py     # Message serialization
│   │               └── _agent_registry.py     # Agent management
│   ├── pyproject.toml         # Python project configuration
│   └── README.md              # Detailed implementation guide
├── pyproject.toml             # Root project metadata
├── service.yml                # Service configuration
└── README.md                  # This file
```

## 📋 Requirements

- **Python**: 3.10 or higher
- **Apache Kafka**: Local cluster or managed service (e.g., Confluent Cloud)
- **Dependencies**: See `python/pyproject.toml` for full list

### Core Dependencies
- `autogen-core>=0.6.1` - Core AutoGen framework
- `confluent-kafka>=2.10.1` - Kafka client
- `kstreams>=0.26.9` - Kafka Streams abstraction
- `cloudevents>=1.12.0` - CloudEvents support

## 🏃 Quick Start

### 1. Installation

Navigate to the Python directory and install dependencies:

```bash
cd python
uv sync --all-extras
```

### 2. Kafka Setup

Ensure your Kafka cluster is running. For local development:

```bash
# Using Docker Compose (example)
docker-compose up -d kafka zookeeper
```

### 3. Basic Usage

```python
from autogen_kafka_extension.worker_config import WorkerConfig
from autogen_kafka_extension.worker_runtime import KafkaWorkerAgentRuntime
from autogen_core.agent import AgentId

# Configure the runtime
config = WorkerConfig(
    request_topic="agent.requests",
    response_topic="agent.responses", 
    group_id="worker-group",
    client_id="worker-client",
    title="My Agent Runtime"
)

# Create and start the runtime
runtime = KafkaWorkerAgentRuntime(config)
await runtime.start()

# Register an agent
await runtime.register_factory("echo", lambda: EchoAgent())

# Send a message
response = await runtime.send_message(
    "Hello World", 
    recipient=AgentId("echo", "instance-001")
)
```

## 🛠 Development

### Running Tests

```bash
cd python
uv run pytest
```

### Development Setup

The project uses:
- **UV** for dependency management and Python tooling
- **pytest** for testing with async support
- **testcontainers** for integration testing with Kafka

## 📖 Documentation

For detailed implementation guides, architecture details, and advanced usage examples, see the [Python README](python/README.md).

## 🤝 Contributing

This repository is part of the Confluent organization on GitHub and is open to contributions from the community.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

Please see the [LICENSE](LICENSE) file for contribution terms.

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🔄 Changelog

See [CHANGELOG.md](CHANGELOG.md) for details of recent updates and version history.

## 🆘 Support

- **Issues**: Report bugs and request features via [GitHub Issues](../../issues)
- **Documentation**: Check the [Python README](python/README.md) for detailed usage
- **Community**: Join discussions in the AutoGen community

---

**Note**: This is an extension for Microsoft AutoGen. Make sure you're familiar with the [core AutoGen concepts](https://github.com/microsoft/autogen) before using this Kafka extension.

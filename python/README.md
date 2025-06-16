# KafkaWorkerAgentRuntime

A scalable, event-driven runtime for autonomous agents powered by Apache Kafka. The `KafkaWorkerAgentRuntime` extends AutoGen's core `AgentRuntime` to enable message-based communication over Kafka topics, with built-in support for pub/sub and RPC-style patterns.

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

## 🚀 Quick Start

### Requirements

- **Python**: 3.10 or higher
- **Apache Kafka**: Local cluster or managed service (e.g., Confluent Cloud)
- **UV**: Recommended for dependency management

Install the required packages using UV:

```bash
uv sync --all-extras
```

### Kafka Setup

Ensure your Kafka cluster is running and accessible. For local development, you can run Kafka using Docker:

```bash
# Example using Docker Compose
docker-compose up -d kafka zookeeper
```

For production environments, consider using managed Kafka services like Confluent Cloud. Update your Kafka configuration accordingly in the `WorkerConfig`.

### Basic Configuration and Startup

Here's a simple example to get the runtime started:

```python
from autogen_kafka_extension.worker_config import WorkerConfig
from autogen_kafka_extension.worker_runtime import KafkaWorkerAgentRuntime

# Configure the runtime
config = WorkerConfig(
    request_topic="agent.requests",
    subscription_topic="agent.responses",
    group_id="worker-group",
    client_id="worker-client",
    title="Agent Runtime"
)

# Create and start the runtime
runtime = KafkaWorkerAgentRuntime(config)
await runtime.start()
```

---

## 🛠 Agent Management

### Registering a Factory

Register agent factories to enable dynamic agent creation:

```python
from autogen_core.agent import AgentId

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
```

### Subscribe to Topics

Set up agents to listen for specific topic messages:

```python
# Agents can subscribe to topics during registration
# This is typically configured in your agent implementation
```

---

## ⚙️ Configuration Options

The `WorkerConfig` class provides extensive configuration options:

```python
config = WorkerConfig(
    # Core Kafka settings
    request_topic="agent.requests",
    subscription_topic="agent.responses",
    group_id="worker-group",
    client_id="worker-client",
    
    # Runtime settings
    title="My Agent Runtime",
    
    # Additional Kafka client settings can be passed
    # through the underlying kstreams configuration
)
```

---

## 📦 Development Notes

### Architecture

- **Stream Processing**: Uses `kstreams` for robust stream abstraction over Kafka
- **Background Tasks**: Robust background task management with exception tracking and recovery
- **Message Format**: Includes CloudEvent deserialization and trace propagation for observability
- **Extensibility**: Built with modularity in mind - plug in your own agents, serializers, and middleware

### Testing

The package includes comprehensive test coverage using:

```bash
cd packages/autogen-kafka-extension

# Run all tests
PYTHONPATH=tests:src uv run python -m pytest tests/test_worker_runtime.py

# Run with coverage
PYTHONPATH=tests:src uv run python -m pytest tests/test_worker_runtime.py --cov=autogen_kafka_extension

```

### Debugging and Monitoring

- **OpenTelemetry Integration**: Built-in tracing for message flow visibility
- **Logging**: Comprehensive logging throughout the runtime lifecycle  
- **Error Handling**: Graceful error recovery with detailed error reporting

---

## 🏗️ Advanced Usage

### Custom Serialization

Implement custom message serialization for specific use cases:

```python
# Custom serializers can be plugged into the runtime
# See the _message_serdes.py module for implementation details
```

### Agent State Management

```python
# Agents can maintain state across message processing
# State persistence strategies depend on your specific requirements
```

### Scaling Considerations

- **Consumer Groups**: Use Kafka consumer groups for horizontal scaling
- **Topic Partitioning**: Design topic partitioning strategy for optimal load distribution
- **Resource Management**: Monitor memory and CPU usage for optimal performance

---

## 📈 Roadmap

- [x] Core Kafka integration with AutoGen
- [x] CloudEvents support
- [x] OpenTelemetry tracing
- [ ] Enhanced agent state persistence mechanisms
- [ ] Agent metadata and discovery service
- [ ] Pluggable metrics exporters (Prometheus, etc.)
- [ ] Advanced CLI tools for monitoring and debugging
- [ ] Docker support for streamlined local development
- [ ] Schema registry integration for advanced serialization
- [ ] Dead letter queue support for error handling
- [ ] Performance optimizations for high-throughput scenarios

---

## 🐛 Troubleshooting

### Common Issues

1. **Kafka Connection Issues**
   - Verify Kafka cluster is accessible
   - Check network connectivity and firewall settings
   - Validate Kafka client configuration

2. **Agent Registration Problems**
   - Ensure agent factories return valid agent instances
   - Check for naming conflicts in agent IDs
   - Verify agent implementations follow AutoGen patterns

3. **Message Delivery Issues**
   - Monitor Kafka topic health and partition assignments
   - Check consumer group status and lag
   - Validate message serialization format

### Performance Tuning

- Adjust Kafka consumer and producer configurations
- Optimize agent processing logic for throughput
- Monitor memory usage and adjust heap sizes as needed
- Consider topic partitioning strategies for load distribution

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](../LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please see the main project [README](../README.md) for contribution guidelines.

---

## 🆘 Support

- **Documentation**: This README and the main project [README](../README.md)
- **Issues**: Report bugs and feature requests via GitHub Issues
- **AutoGen Resources**: [Microsoft AutoGen Documentation](https://github.com/microsoft/autogen)
- **Kafka Resources**: [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
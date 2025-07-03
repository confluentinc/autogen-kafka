# AutoGen Kafka Extension - Documentation

Welcome to the comprehensive documentation for the AutoGen Kafka Extension. This documentation covers everything from basic usage to advanced architecture and troubleshooting.

## 📖 Documentation Structure

### 🚀 Getting Started
- **[Main README](../../../README.md)** - Installation, quick start, and basic examples
- **[API Overview](api/README.md)** - Comprehensive API documentation and architecture overview

### 🏗️ Development
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Development setup, patterns, and contribution guidelines
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues, debugging tools, and solutions

### 📊 Architecture & Design

#### System Overview
The AutoGen Kafka Extension enables distributed multi-agent systems through Apache Kafka messaging:

```
┌─────────────────────────────────────────────────────────────────┐
│                  AutoGen Multi-Agent System                     │
├─────────────────────────────────────────────────────────────────┤
│           Local Agents    ←→    Kafka Extension                 │
│                                        ↕                        │
│                               Apache Kafka                      │
│                                        ↕                        │
│          Remote Agents    ←→   External Services                │
└─────────────────────────────────────────────────────────────────┘
```

#### Key Components
1. **Runtime Layer**: Manages distributed agent lifecycle and communication
2. **Agent Layer**: Bridges AutoGen agents with Kafka topics
3. **Services Layer**: Handles registration, subscriptions, and message processing
4. **Events Layer**: Provides type-safe serialization and CloudEvents integration
5. **Configuration Layer**: Manages complex configuration with validation

### 🔧 Usage Patterns

#### Pattern 1: Distributed Agent Runtime
```python
# Multiple runtimes coordinating across processes/machines
runtime1 = KafkaWorkerAgentRuntime(config_worker1)
runtime2 = KafkaWorkerAgentRuntime(config_worker2)

# Agents can communicate across runtimes
await runtime1.send_message(message, agent_id_on_runtime2)
```

#### Pattern 2: Kafka Bridge Agent
```python
# Bridge AutoGen agents with external Kafka services
bridge = KafkaStreamingAgent(
    config=bridge_config,
    description="External API Bridge",
    request_type=RequestType,
    response_type=ResponseType,
)
await bridge.send_message(request, external_service_topic)
```

#### Pattern 3: Hybrid Architecture
```python
# Mix local and distributed agents
local_runtime = SingleThreadedAgentRuntime()
kafka_runtime = KafkaWorkerAgentRuntime(kafka_config)

# Some agents local, others distributed
await local_runtime.register_factory("local_agent", LocalAgent)
await kafka_runtime.register_factory("distributed_agent", DistributedAgent)
```

### 🔍 Component Deep Dive

#### Configuration System
- **Hierarchical**: Base classes with specialized configurations
- **Validated**: Automatic validation with detailed error messages
- **Flexible**: Support for environment variables and complex scenarios

#### Event System
- **Type-Safe**: Strong typing with runtime validation
- **Standards-Based**: Built on CloudEvents specification
- **Schema-Aware**: Integration with Confluent Schema Registry

#### Monitoring & Observability
- **Distributed Tracing**: OpenTelemetry integration
- **Metrics**: Prometheus metrics for all components
- **Health Checks**: Built-in health monitoring

### 🛠️ Advanced Topics

#### Performance Optimization
- Connection pooling and batch processing
- Kafka configuration tuning
- Agent optimization patterns

#### Security
- Kafka security configuration (SASL, SSL)
- Input validation and sanitization
- Secret management best practices

#### Testing
- Unit testing with mocks and fixtures
- Integration testing with real Kafka
- Performance testing and benchmarking

### 📋 Quick Reference

#### Common Commands
```bash
# Health checks
kafka-topics --bootstrap-server localhost:9092 --list
curl http://localhost:8081/subjects

# Development setup
uv pip install -e .[dev]
docker-compose up -d

# Testing
pytest tests/
pytest -m integration  # Integration tests only
```

#### Configuration Examples
```python
# Basic worker configuration
config = KafkaAgentRuntimeConfig(
    kafka_config=KafkaConfig(bootstrap_servers=["localhost:9092"]),
    name="my-worker",
    group_id="agents",
    request_topic="requests",
    response_topic="responses"
)

# Agent bridge configuration  
agent_config = KafkaAgentConfig(
    kafka_config=kafka_config,
    request_topic="external.requests",
    response_topic="external.responses"
)
```

#### Debugging
```python
# Enable debug logging
import logging
logging.getLogger('autogen_kafka_extension').setLevel(logging.DEBUG)

# Monitor metrics
print(f"Pending requests: {len(agent._pending_requests)}")
print(f"Background tasks: {len(task_manager._background_tasks)}")
```

### 🤝 Contributing

We welcome contributions! Please see the [Developer Guide](DEVELOPER_GUIDE.md) for:
- Development setup and workflow
- Coding standards and patterns
- Testing requirements
- Documentation guidelines

### 📞 Support

- **Issues**: [GitHub Issues](https://github.com/microsoft/autogen-kafka/issues)
- **Documentation**: This documentation set
- **Examples**: Check the examples directory
- **Community**: Join discussions in GitHub Discussions

### 📚 Related Resources

- **[AutoGen Framework](https://github.com/microsoft/autogen)** - Core multi-agent framework
- **[Apache Kafka](https://kafka.apache.org/)** - Distributed streaming platform
- **[CloudEvents](https://cloudevents.io/)** - Event specification standard
- **[OpenTelemetry](https://opentelemetry.io/)** - Observability framework

---

**Need help?** Check the [Troubleshooting Guide](TROUBLESHOOTING.md) or open an issue with your question. 
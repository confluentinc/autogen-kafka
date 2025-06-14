# KafkaWorkerAgentRuntime

KafkaWorkerAgentRuntime is a scalable, event-driven runtime for autonomous agents powered by Apache Kafka. It extends `AgentRuntime` to enable message-based communication over Kafka topics, with built-in support for pub/sub and RPC-style patterns.

---

## 📌 Features

- **Agent Lifecycle Management** – Dynamically register agent factories and instances
- **Kafka Message Routing** – Built-in pub/sub and RPC using Kafka topics
- **Streaming Engine** – Uses `kstreams` for asynchronous event processing
- **Serialization & Schema Support** – JSON and CloudEvents-based payloads
- **Observability** – Integrated OpenTelemetry tracing
- **Fault Handling** – Safe background task management with traceable errors

---

## 🚀 Quick Start

### Requirements

- Python 3.10+
- Kafka cluster (local or remote)
- Install the required packages using UV:

```bash
uv sync --all-extras
```

Make sure to configure your Kafka connection details in the runtime configuration.

### Kafka Setup

Ensure your Kafka cluster is running and accessible. You can run Kafka locally using Docker:

```bash
docker-compose up -d
```

Or use a managed Kafka service like Confluent Cloud. Update your Kafka configuration accordingly in the `WorkerConfig`.

### Example Usage

Here's a simple example to get the runtime started with a basic configuration:

```python
from autogen_kafka_extension.worker_config import WorkerConfig
from autogen_kafka_extension.worker_runtime import KafkaWorkerAgentRuntime

config = WorkerConfig(
    request_topic="agent.requests",
    response_topic="agent.responses",
    group_id="worker-group",
    client_id="worker-client",
    title="Agent Runtime"
)

runtime = KafkaWorkerAgentRuntime(config)
await runtime.start()
```

---

## 🛠 Agent Management

### Registering a Factory

```python
await runtime.register_factory("echo", lambda: EchoAgent())
```

### Registering an Instance

```python
agent_id = AgentId("echo", "instance-001")
await runtime.register_agent_instance(EchoAgent(), agent_id)
```

---

## 📤 Messaging

### Send a Message (RPC-style)

```python
response = await runtime.send_message("Hello", recipient=AgentId("echo", "instance-001"))
```

### Publish a Message (Broadcast)

```python
await runtime.publish_message("Announcement", topic_id=TopicId("event", "broadcast"))
```

---

## 📦 Development Notes

- Uses `kstreams` for stream abstraction over Kafka
- Robust background task management with exception tracking
- Includes CloudEvent deserialization and trace propagation
- Built with extensibility in mind: plug in your own agents, serializers, and middleware

---

## 📈 Roadmap

- [ ] Agent state persistence
- [ ] Agent metadata service
- [ ] Pluggable metrics exporter
- [ ] Improved CLI for monitoring and debugging
- [ ] Docker support for local development and testing

---

## 📄 License

MIT or enterprise license (depending on usage context)
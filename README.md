# Autogen Kafka Extension

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A scalable, event-driven extension for [Microsoft AutoGen](https://github.com/microsoft/autogen) that enables **distributed multi-agent systems** using Apache Kafka. Break free from single-machine limitations and build agent systems that scale across multiple processes, machines, and even programming languages.

## 🤔 What Problem Does This Solve?

**Standard AutoGen Problem**: Your agents are stuck on one machine. If you want multiple agents to collaborate across different processes, machines, or with external services, you're out of luck.

**Our Solution**: This extension provides three key building blocks to create truly distributed agent systems:

## 🏗️ Core Components Explained

### 1. 🏃‍♂️ **Agent Runtime** - Distributed Agent Coordination
**What it is**: A distributed coordination system that allows AutoGen agents running on different machines to find each other and communicate seamlessly.

**When to use**:
- You have agents that need to run on separate machines (e.g., different cloud instances)
- You want to scale your agent system horizontally 
- You need agents in different programming languages to work together
- You want fault-tolerant agent systems where some agents can fail without breaking everything

**Real example**: 
```python
# Machine 1: Data processing agents
runtime_1 = KafkaAgentRuntime(config_machine_1)
await runtime_1.register_factory("data_processor", DataProcessorAgent)

# Machine 2: Analysis agents  
runtime_2 = KafkaAgentRuntime(config_machine_2)
await runtime_2.register_factory("data_analyzer", AnalyzerAgent)

# Agents can now communicate across machines automatically
await runtime_1.send_message(
    message=ProcessRequest(data="sales_data.csv"),
    recipient=AgentId(type="data_analyzer", key="default")
)
```

### 2. 🌉 **Streaming Agent** - External System Bridge
**What it is**: A special agent that acts as a bridge between your AutoGen agents and external Kafka-based services or systems.

**When to use**:
- You want to connect AutoGen agents with external microservices
- You need to integrate with existing Kafka-based systems  
- You want to expose AutoGen capabilities to non-AutoGen applications
- You're building hybrid architectures (some AutoGen, some external services)

**Real example**:
```python
# Bridge to external sentiment analysis service
sentiment_bridge = KafkaStreamingAgent(
    config=bridge_config,
    description="External sentiment analysis service",
    request_type=SentimentRequest,  # What you send
    response_type=SentimentResponse  # What you get back
)

# Now your AutoGen agents can use external services transparently
response = await sentiment_bridge.send_message(
    SentimentRequest(text="I love this product!")
)
# response.sentiment == "positive" (from external service)
```

### 3. 🧠 **Distributed Memory** - Shared Agent Memory
**What it is**: A memory system that keeps agent memory synchronized across multiple instances using Kafka, so all agents share the same conversation history and context.

**When to use**:
- You have multiple instances of the same agent type
- You need conversation history to persist across agent restarts
- You want different agent instances to learn from each other's interactions
- You're building stateful agent systems that need to remember past conversations

**Real example**:
```python
# All customer service agents share the same memory
shared_memory = KafkaMemory(config, session_id="customer_service")

# Agent instance 1 learns something
await shared_memory.add("Customer John prefers email contact")

# Agent instance 2 (on different machine) instantly knows this
query_result = await shared_memory.query("John contact preference")
# Returns: "Customer John prefers email contact"
```

## 🚀 Quick Start Examples

### Example 1: Multi-Machine Agent System
```python
# Deploy these on different machines with same Kafka cluster

# machine_1.py - Specialized for data processing
runtime = KafkaAgentRuntime(config)
await runtime.register_factory("data_processor", DataProcessor)
await runtime.start()

# machine_2.py - Specialized for analysis  
runtime = KafkaAgentRuntime(config)
await runtime.register_factory("analyzer", AnalyzerAgent)
await runtime.start()

# machine_3.py - Orchestrator
runtime = KafkaAgentRuntime(config)
# Can send work to any agent on any machine
result = await runtime.send_message(
    ProcessRequest(data="financial_data.xlsx"),
    recipient=AgentId("data_processor", "default")
)
```

### Example 2: Hybrid Architecture (AutoGen + External Services)
```python
# Connect AutoGen agents with external ML service
class MLServiceBridge(KafkaStreamingAgent):
    async def on_message_impl(self, message, ctx):
        # Forward to external ML service via Kafka
        return await self.call_external_service(message)

# Use in your agent workflow
class BusinessAgent(Agent):
    async def process_request(self, data):
        # Use external ML service through the bridge
        ml_result = await self.send_message(
            MLRequest(data=data),
            recipient=AgentId("ml_service_bridge", "default")
        )
        return self.make_business_decision(ml_result)
```

### Example 3: Scalable Customer Service
```python
# Multiple customer service agents sharing memory
class CustomerServiceAgent(Agent):
    def __init__(self):
        # Shared memory across all customer service instances
        self.memory = KafkaMemory(config, session_id="customer_service")
    
    async def handle_customer(self, customer_id, question):
        # Check what we know about this customer
        history = await self.memory.query(f"customer {customer_id}")
        
        # Process with context
        response = await self.process_with_history(question, history)
        
        # Remember for next time (all instances will know)
        await self.memory.add(f"Customer {customer_id}: {question} -> {response}")
        
        return response

# Deploy multiple instances - they all share the same memory
```

## 🔄 Architecture Patterns

### Pattern 1: Microservices with Agents
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Service  │    │  Order Service  │    │Payment Service  │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │AutoGen Agent│ │    │ │AutoGen Agent│ │    │ │AutoGen Agent│ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                        ┌─────────────────┐
                        │  Kafka Runtime  │
                        │   (Coordinator) │
                        └─────────────────┘
```

### Pattern 2: Hybrid AI Pipeline
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  AutoGen Agents │    │ Streaming Agent │    │External ML/API  │
│   (Reasoning)   │────┤     (Bridge)    │────┤   Services      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Pattern 3: Multi-Language Agent System
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Python Agents   │    │    C# Agents    │    │   JS Agents     │
│                 │    │                 │    │                 │
│ KafkaRuntime    │    │ KafkaRuntime    │    │ KafkaRuntime    │
│ (Python)        │    │ (.NET - Future) │    │ (Future)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                           Kafka Cluster
                      (Language-agnostic messaging)
```

## 📦 Installation

```bash
# Basic installation
uv add autogen-kafka-extension

# Development installation
git clone https://github.com/microsoft/autogen-kafka.git
cd autogen-kafka/python/packages/autogen-kafka-extension
uv pip install -e .[dev]
```

## 🛠️ Setup Requirements

### Prerequisites
- **Python 3.10+** with [uv](https://docs.astral.sh/uv/) package manager (recommended)
- **Kafka cluster** (local or cloud)

### Kafka Infrastructure
You need a Kafka cluster (local or cloud):

**Option 1: Local Development**
```bash
# Quick start with Docker
docker-compose up -d
```

**Option 2: Confluent Cloud (Recommended for production)**
- Create Confluent Cloud account
- Set up Kafka cluster and Schema Registry
- Configure API keys

### Quick Setup with uv
```bash
# Clone and setup the project
git clone https://github.com/microsoft/autogen-kafka.git
cd autogen-kafka/python/packages/exemple
uv sync  # Install all dependencies
python main.py  # Run the example
```

### Configuration
Create your configuration file:

```yaml
# config.yml
kafka:
  bootstrap_servers: "localhost:9092"  # or your cloud broker
  group_id: "my_agent_group"
  
runtime:
  runtime_requests: "agent_requests"
  runtime_responses: "agent_responses" 
  registry_topic: "agent_registry"
  subscription_topic: "subscriptions"
  publish_topic: "agent_messages"
```

## 📊 When to Use Each Component

| Component | Use When | Don't Use When |
|-----------|----------|----------------|
| **Runtime** | • Multiple machines<br>• Horizontal scaling<br>• Cross-language agents<br>• Fault tolerance | • Single machine<br>• Simple agent chat<br>• No scaling needed |
| **Streaming Agent** | • External service integration<br>• Kafka-based systems<br>• Hybrid architectures<br>• Non-AutoGen services | • Pure AutoGen workflows<br>• No external dependencies<br>• Simple agent-to-agent chat |
| **Distributed Memory** | • Multiple agent instances<br>• Shared state needed<br>• Persistent conversations<br>• Cross-instance learning | • Single agent instance<br>• No shared state<br>• Ephemeral conversations |

## 🧪 Live Example

We provide a complete working example:

```bash
cd python/packages/exemple
uv sync  # Install dependencies
python main.py
```

This demonstrates:
- **Distributed agents** (one local Python, one remote Flink)
- **External service integration** (OpenAI via Flink SQL)
- **Real-time messaging** (sentiment analysis pipeline)
- **Production setup** (Confluent Cloud infrastructure)

## 🗂️ Project Structure

```
autogen-kafka/
├── python/packages/autogen-kafka-extension/
│   ├── src/autogen_kafka_extension/
│   │   ├── runtimes/           # 🏃‍♂️ Distributed coordination
│   │   │   ├── kafka_agent_runtime.py
│   │   │   └── services/       # Agent discovery, messaging, subscriptions
│   │   ├── agent/              # 🌉 External system bridges  
│   │   │   └── kafka_streaming_agent.py
│   │   ├── memory/             # 🧠 Distributed memory
│   │   │   └── kafka_memory.py
│   │   └── config/             # Configuration management
│   └── tests/
├── python/packages/exemple/    # Working examples
└── docs/                       # Detailed documentation
```

## 🤝 Contributing

This project welcomes contributions:

1. **Core Architecture**: Message protocols, event schemas
2. **Language Implementations**: C#, JavaScript, Java runtimes  
3. **Integration Examples**: Real-world usage patterns
4. **Documentation**: Guides, tutorials, API docs

### Development Setup
```bash
# Fork the repo and clone your fork
git clone https://github.com/your-username/autogen-kafka.git
cd autogen-kafka

# Install development dependencies with uv
cd python/packages/autogen-kafka-extension
uv pip install -e .[dev]

# Run tests
pytest
```

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) file.

## 🔗 Related Projects

- [Microsoft AutoGen](https://github.com/microsoft/autogen) - Core agent framework
- [Apache Kafka](https://kafka.apache.org/) - Distributed streaming platform  
- [Confluent Cloud](https://confluent.cloud/) - Managed Kafka service

---

**Ready to scale your agents?** Start with our [quick examples](python/packages/exemple/) or dive into the [detailed documentation](python/packages/autogen-kafka-extension/docs/).

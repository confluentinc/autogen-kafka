# AutoGen Kafka Extension - Sample Application

This directory contains a complete sample application demonstrating how to use the AutoGen Kafka Extension with both Kafka and GRPC runtimes.

## 🎯 What This Sample Demonstrates

- **Multiple Runtime Support**: Choose between Kafka and GRPC runtimes at startup
- **Agent Configuration**: Load configuration from external YAML files
- **Interactive Processing**: Command-line interface for sentiment analysis
- **Proper Lifecycle Management**: Handles startup, processing, and shutdown
- **Error Handling**: Graceful error handling and resource cleanup
- **Type-Safe Messages**: Define request/response types with JSON schema validation

## 🚀 Quick Start

### Prerequisites

1. **Start Kafka Infrastructure** (if using Kafka runtime):
   ```bash
   cd ../../../
   docker-compose up -d
   ```

2. **Install Dependencies**:
   ```bash
   cd python/packages/exemple
   pip install -r requirements.txt
   ```

### Running the Sample

```bash
python main.py
```

**Interactive prompts:**
1. Choose whether to enable debug logging (y/N)
2. Select runtime: Kafka (default) or GRPC
3. Enter text for sentiment analysis
4. Type 'exit' to quit

### Sample Session

```
$ python main.py
Do you want to enable logs (y/N): y
Select the runtime to use: Kafka or GRPC (Default: Kafka)?
Please specify a text to analyze or type 'exit' to quit the application: I love this framework!
Analyzing sentiment for text: I love this framework!
Sentiment analysis result: positive
Please specify a text to analyze or type 'exit' to quit the application: exit
```

## 📁 File Structure

```
packages/exemple/
├── main.py                # Main application entry point
├── sample.py              # Base Sample class (abstract interface)
├── kafka_sample.py        # Kafka runtime implementation
├── grpcs_sample.py        # GRPC runtime implementation
├── events.py              # Message type definitions
├── sample.config.yml      # Configuration file
└── README.md              # This file
```

## 🔧 Configuration

### Configuration File (`sample.config.yml`)

```yaml
kafka:
    name: "simple_kafka"
    bootstrap_servers: "localhost:9092"  # Change for your Kafka cluster
    group_id: "simple_group_abc"
    client_id: "simple_client_abc"
    # Add security settings if needed:
    # sasl_plain_username: "[USERNAME]"
    # sasl_plain_password: "[PASSWORD]"
    # security_protocol: "SASL_SSL"
    # sasl_mechanism: "PLAIN"
    # schema_registry:
    #     url: "[SCHEMA_REGISTRY_URL]"
    #     api_key: "[API_KEY]"
    #     api_secret: "[API_SECRET]"
    
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

### For Cloud Kafka Services

Update the configuration for cloud services like Confluent Cloud:

```yaml
kafka:
    name: "cloud_kafka"
    bootstrap_servers: "[YOUR_BOOTSTRAP_SERVERS]"
    group_id: "your_group"
    client_id: "your_client"
    sasl_plain_username: "[YOUR_USERNAME]"
    sasl_plain_password: "[YOUR_PASSWORD]"
    security_protocol: "SASL_SSL"
    sasl_mechanism: "PLAIN"
    schema_registry:
        url: "[YOUR_SCHEMA_REGISTRY_URL]"
        api_key: "[YOUR_API_KEY]"
        api_secret: "[YOUR_API_SECRET]"
```

## 🏗️ Architecture Overview

### Base Interface (`sample.py`)

The `Sample` class provides a common interface for both runtime implementations:

```python
class Sample(ABC):
    def __init__(self, runtime): ...
    def is_running(self) -> bool: ...
    async def new_agent(self) -> Agent: ...
    async def start(self): ...
    async def get_sentiment(self, text: str) -> SentimentResponse: ...
    async def stop(self): ...
```

### Runtime Implementations

#### Kafka Runtime (`kafka_sample.py`)
- Uses `KafkaAgentRuntime` for distributed processing
- Suitable for horizontal scaling
- Supports multiple instances across different machines

#### GRPC Runtime (`grpcs_sample.py`)
- Uses `GrpcWorkerAgentRuntime` for fast local communication
- Suitable for single-machine deployments
- Lower latency for local operations

### Message Types (`events.py`)

Type-safe message definitions with JSON schema validation:

```python
@dataclass
class SentimentRequest(KafkaMessageType):
    text: str

@dataclass
class SentimentResponse(KafkaMessageType):
    sentiment: str
```

## 🛠️ Extending the Sample

### Adding New Message Types

1. **Define the message types** in `events.py`:
   ```python
   @dataclass
   class AnalysisRequest(KafkaMessageType):
       text: str
       analysis_type: str
       
   @dataclass
   class AnalysisResponse(KafkaMessageType):
       result: str
       confidence: float
   ```

2. **Update the agent configuration** in `sample.py`:
   ```python
   agent = KafkaStreamingAgent(
       config=self._agent_config,
       description="Multi-purpose analysis agent",
       response_type=AnalysisResponse,
       request_type=AnalysisRequest,
   )
   ```

3. **Add new methods** to the `Sample` class:
   ```python
   async def analyze_text(self, text: str, analysis_type: str) -> AnalysisResponse:
       response = await self._runtime.send_message(
           message=AnalysisRequest(text=text, analysis_type=analysis_type),
           recipient=AgentId(type="analysis_agent", key="default")
       )
       return response
   ```

### Adding New Runtime Types

1. **Create a new runtime implementation**:
   ```python
   class WebSocketSample(Sample):
       def __init__(self):
           runtime = WebSocketAgentRuntime("ws://localhost:8080")
           super().__init__(runtime=runtime)
       
       async def _start(self):
           await self._runtime.start()
       
       async def stop(self):
           await self._runtime.stop()
   ```

2. **Update the main application** to include the new option:
   ```python
   runtime_choice = input("Select runtime (Kafka/GRPC/WebSocket): ")
   if runtime_choice.upper() == "WEBSOCKET":
       self.exemple = WebSocketSample()
   ```

## 🧪 Testing

### Unit Tests

```python
import pytest
from packages.exemple.kafka_sample import KafkaSample
from packages.exemple.events import SentimentRequest

@pytest.mark.asyncio
async def test_kafka_sample():
    sample = KafkaSample()
    await sample.start()
    
    response = await sample.get_sentiment("test text")
    assert response.sentiment is not None
    
    await sample.stop()
```

### Integration Tests

```python
@pytest.mark.integration
async def test_full_flow():
    # Test both runtime types
    for sample_class in [KafkaSample, GRPCSample]:
        sample = sample_class()
        await sample.start()
        
        response = await sample.get_sentiment("positive text")
        assert response.sentiment == "positive"
        
        await sample.stop()
```

## 📚 Learning Resources

- **[AutoGen Documentation](https://github.com/microsoft/autogen)** - Core concepts
- **[Kafka Documentation](https://kafka.apache.org/documentation/)** - Kafka configuration
- **[Main README](../../../README.md)** - Architecture overview
- **[Python Package README](../README.md)** - Python-specific documentation

## 🤝 Contributing

This sample application is designed to be educational and extensible. Feel free to:

1. **Add new runtime types** following the existing pattern
2. **Extend message types** with more complex data structures
3. **Add more sophisticated agents** with different capabilities
4. **Improve error handling** and logging
5. **Add more configuration options** for different deployment scenarios

## 🔍 Troubleshooting

### Common Issues

1. **Kafka connection failed**:
   - Ensure Kafka is running: `docker-compose up -d`
   - Check bootstrap servers in configuration
   - Verify network connectivity

2. **GRPC connection failed**:
   - Ensure GRPC host is running
   - Check port availability
   - Verify firewall settings

3. **Configuration errors**:
   - Validate YAML syntax
   - Check all required fields are present
   - Verify topic names are valid

### Debug Mode

Enable debug logging to see detailed information:

```bash
python main.py
# Choose 'y' when prompted about enabling logs
```

This will show:
- Kafka connection details
- Message serialization/deserialization
- Agent lifecycle events
- Runtime state changes

## 📄 License

This sample application is part of the AutoGen Kafka Extension and is licensed under the Apache License 2.0. 
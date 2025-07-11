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

1. **Confluent Cloud Setup** (for Kafka runtime):
   - Create a Confluent Cloud account
   - Set up a Kafka cluster
   - Create the required topics: `simple_request_topic` and `simple_response_topic`
   - Set up Schema Registry
   - Configure API keys and connection details

2. **Flink SQL Job** (Remote Agent):
   - Deploy the Flink SQL job from `flink.sql` to your Flink cluster
   - The job creates a sentiment analysis model using OpenAI
   - It processes messages from `simple_request_topic` and sends results to `simple_response_topic`

3. **Install Dependencies**:
   ```bash
   cd python/packages/exemple
   uv sync
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

This example is configured for **Confluent Cloud**. Update the configuration with your Confluent Cloud credentials:

```yaml
kafka:
    name: "simple_kafka"
    bootstrap_servers: "[YOUR_CONFLUENT_CLOUD_BOOTSTRAP_SERVERS]:9092"
    group_id: "simple_group_abc"
    client_id: "simple_client_abc"
    sasl_plain_username: "[YOUR_CONFLUENT_CLOUD_API_KEY]"
    sasl_plain_password: "[YOUR_CONFLUENT_CLOUD_API_SECRET]"
    security_protocol: "SASL_SSL"
    sasl_mechanism: "PLAIN"
    schema_registry:
        url: "[YOUR_CONFLUENT_CLOUD_SCHEMA_REGISTRY_URL]"
        api_key: "[YOUR_SCHEMA_REGISTRY_API_KEY]"
        api_secret: "[YOUR_SCHEMA_REGISTRY_API_SECRET]"
    
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

### Required Confluent Cloud Setup

Before running the example, ensure you have:

1. **Created the required topics** in your Confluent Cloud cluster:
   - `simple_request_topic`
   - `simple_response_topic`
   - `runtime_requests`
   - `runtime_responses`
   - `agent_registry`
   - `agent_subscription`
   - `publish`

2. **Schema Registry** enabled and configured with API keys

3. **Flink SQL Job** deployed (see Remote Agent section below)

## 🏗️ Architecture Overview

This example demonstrates a **distributed sentiment analysis system** using:
- **AutoGen Kafka Extension** for the client-side agent
- **Confluent Cloud** for messaging infrastructure
- **Flink SQL** for the remote sentiment analysis agent

### System Flow

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Python App    │    │ Confluent Cloud │    │   Flink SQL     │
│ (Local Agent)   │───▶│   Kafka Topics  │───▶│ (Remote Agent)  │
│                 │    │                 │    │                 │
│ KafkaStreaming  │    │ request_topic   │    │ ML_PREDICT      │
│ Agent           │◀───│ response_topic  │◀───│ (OpenAI Model)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Remote Agent (Flink SQL Job)

The sentiment analysis is performed by a **Flink SQL job** deployed on your Flink cluster:

```sql
-- Create Model
CREATE MODEL sentimentmodel
       INPUT(text STRING)
       OUTPUT(sentiment STRING) COMMENT 'sentiment analysis model'
       WITH (
          'provider' = 'openai',
          'task' = 'classification',
          'openai.connection' = 'openai-cli-connection',
          'openai.system_prompt' = 'You are specialized in sentiment analysis. Your job is to analyze the sentiment of the text and provide the sentiment score. The sentiment score is positive, negative, or neutral.'
        );

-- Insert the response from the model
INSERT INTO `simple_response_topic`
    SELECT s.key, s.id, ROW(p.sentiment) AS message, s.message_type
    FROM `simple_request_topic` AS s, LATERAL TABLE (ML_PREDICT('sentimentmodel', `message`.`text`)) AS p(sentiment)
```

**What this Flink job does:**
1. **Creates a sentiment analysis model** using OpenAI's API
2. **Listens to `simple_request_topic`** for incoming text analysis requests
3. **Processes each message** through the [ML_PREDICT function](https://docs.confluent.io/cloud/current/flink/reference/functions/model-inference-functions.html)
4. **Sends results to `simple_response_topic`** for the client to consume

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
- Connects to Confluent Cloud
- Communicates with the remote Flink SQL agent

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
        request_type=AnalysisRequest,
        response_type=AnalysisResponse,
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

### Deploying the Flink SQL Job

1. **Access your Flink cluster** (Confluent Cloud or standalone Flink)

2. **Set up OpenAI connection**:
   ```sql
   -- Create OpenAI connection (adjust based on your Flink environment)
   CREATE CONNECTION `openai-cli-connection` AS (
       'provider' = 'openai',
       'openai.api_key' = '[YOUR_OPENAI_API_KEY]'
   );
   ```

3. **Deploy the sentiment analysis job**:
   ```bash
   # Copy the flink.sql content to your Flink SQL client
   # Or deploy via Flink SQL CLI
   flink-sql-client --file flink.sql
   ```

4. **Monitor the job**:
   - Check that the job is running and processing messages
   - Monitor the topics for message flow
   - Verify OpenAI API calls are successful

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
from packages.exemple.src.modules.kafka_sample import KafkaSample
from packages.exemple.src.modules import SentimentRequest


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

1. **Confluent Cloud connection failed**:
   - Verify your Confluent Cloud API key and secret
   - Check that your cluster is active and accessible
   - Ensure the bootstrap servers URL is correct
   - Verify your Schema Registry credentials

2. **Topic not found errors**:
   - Ensure all required topics are created in Confluent Cloud
   - Check topic names match exactly with configuration
   - Verify topic permissions for your API key

3. **Flink SQL job issues**:
   - Ensure OpenAI connection is properly configured
   - Check that the Flink job is running and processing messages
   - Verify OpenAI API key has sufficient credits
   - Monitor Flink job logs for errors

4. **Schema Registry errors**:
   - Verify Schema Registry is enabled in Confluent Cloud
   - Check Schema Registry API key and secret
   - Ensure schemas are compatible with message types

5. **Configuration errors**:
   - Validate YAML syntax
   - Check all required fields are present (especially credentials)
   - Verify topic names are valid Kafka topic names

### Debug Mode

Enable debug logging to see detailed information:

```bash
python main.py
# Choose 'y' when prompted about enabling logs
```

This will show:
- Confluent Cloud connection details
- Message serialization/deserialization
- Agent lifecycle events
- Runtime state changes
- Schema Registry interactions

### Monitoring the System

1. **Confluent Cloud Console**:
   - Monitor topic throughput and consumer lag
   - Check Schema Registry activity
   - View cluster metrics

2. **Flink Job Monitoring**:
   - Check job status in Flink dashboard
   - Monitor message processing rates
   - View job logs for errors

3. **OpenAI API Usage**:
   - Monitor API call volume and usage
   - Check for rate limiting or quota issues
   - Verify model responses are as expected

## 📄 License

This sample application is part of the AutoGen Kafka Extension and is licensed under the Apache License 2.0. 
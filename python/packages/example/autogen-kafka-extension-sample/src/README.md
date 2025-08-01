# AutoGen Kafka Extension - Sample Application Source

This directory contains the source code for the AutoGen Kafka Extension sample application, demonstrating distributed sentiment analysis using Kafka and Flink.

## 📁 Directory Structure

```
src/
├── main.py                 # Main application entry point
├── flink.sql              # Flink SQL job for sentiment analysis
├── agent_config.yml       # Agent-specific Kafka configuration
├── config_worker1.yml     # Worker 1 runtime configuration
├── config_worker2.yml     # Worker 2 runtime configuration
├── .gitignore            # Git ignore patterns
└── modules/
    ├── __init__.py       # Module initialization
    ├── events.py         # Message type definitions
    └── forwarding_agent.py # Forwarding agent implementation
```

## 🚀 Quick Start

### Prerequisites

1. **Confluent Cloud Setup**:
   - Kafka cluster with required topics
   - Schema Registry enabled
   - API keys configured

2. **Flink Environment**:
   - Flink cluster with OpenAI connector
   - Deployed sentiment analysis job

### Running the Application

```bash
# From the src directory
python main.py
```

**Interactive Flow**:
1. Enable/disable debug logging
2. Application creates dual runtime instances
3. Input text for sentiment analysis
4. View results from Flink processing
5. Type 'exit' to shutdown gracefully

## 🔧 Core Components

### Main Application (`main.py`)

The central orchestrator that:
- **Dual Runtime Setup**: Creates both Flink and Forwarder runtime instances
- **Interactive Interface**: Command-line interface for user input
- **Message Flow**: Coordinates request/response between local and remote agents
- **Lifecycle Management**: Handles startup, processing, and graceful shutdown

Key features:
```python
class Application:
    def __init__(self):
        self.flink_runtime: KafkaAgentRuntime | None = None
        self.forwarder_runtime: KafkaAgentRuntime | None = None

    async def start(self):
        # Setup dual runtime instances
        # Enable interactive processing
        
    async def process_requests(self):
        # Handle sentiment analysis requests
```

### Flink SQL Job (`flink.sql`)

Defines the remote sentiment analysis service:

```sql
-- Creates OpenAI-powered sentiment analysis model
CREATE MODEL sentimentmodel
    INPUT(text STRING)
    OUTPUT(sentiment STRING)
    WITH (
        'provider' = 'openai',
        'task' = 'classification',
        'openai.system_prompt' = '...'
    );

-- Processes messages from request topic to response topic
INSERT INTO `agent_response_topic`
    SELECT s.key, s.id, ROW(p.sentiment) AS message, s.message_type
    FROM `agent_request_topic` AS s, 
    LATERAL TABLE (ML_PREDICT('sentimentmodel', `message`.`text`)) AS p(sentiment)
```

**Deployment**: Deploy this SQL to your Flink cluster before running the application.

### Configuration Files

#### Agent Configuration (`agent_config.yml`)
- **Purpose**: Base agent configuration for Kafka connectivity
- **Topics**: `agent_request_topic`, `agent_response_topic`
- **Contains**: Confluent Cloud credentials and Schema Registry settings

#### Worker Configurations (`config_worker1.yml`, `config_worker2.yml`)
- **Purpose**: Runtime-specific configurations for different worker instances
- **Difference**: Different group IDs and client IDs for parallel processing
- **Usage**: Worker1 for Flink runtime, Worker2 for Forwarder runtime

### Message Types (`modules/events.py`)

Type-safe message definitions with JSON schema validation:

```python
@dataclass
class SentimentRequest(KafkaMessageType):
    text: str
    
    @staticmethod
    def __schema__() -> str:
        return """
        {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }
        """

@dataclass
class SentimentResponse(KafkaMessageType):
    sentiment: str
```

### Forwarding Agent (`modules/forwarding_agent.py`)

Local agent that:
- **Receives**: User input from the main application
- **Forwards**: Requests to the remote Flink-based sentiment analysis service
- **Returns**: Processed results back to the user interface

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   main.py       │    │ Confluent Cloud │    │   Flink SQL     │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ agent_request_  │    │ sentimentmodel  │
│ │Forwarder    │ │───▶│ topic           │───▶│                 │
│ │Runtime      │ │    │                 │    │ ML_PREDICT      │
│ └─────────────┘ │    │ agent_response_ │    │ (OpenAI)        │
│                 │◀───│ topic           │◀───│                 │
│ ┌─────────────┐ │    │                 │    │                 │
│ │Flink        │ │    │                 │    │                 │
│ │Runtime      │ │    │                 │    │                 │
│ └─────────────┘ │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔒 Configuration Security

### Important Security Notes

⚠️ **Warning**: The configuration files contain sensitive credentials. In production:

1. **Use Environment Variables**:
   ```bash
   export CONFLUENT_API_KEY="your-api-key"
   export CONFLUENT_API_SECRET="your-api-secret"
   ```

2. **External Configuration**:
   ```python
   # Load from external secure config
   config = load_config_from_vault()
   ```

3. **Git Ignore**: Ensure credentials are not committed to version control

### Required Topics

Before running, create these topics in Confluent Cloud:
- `agent_request_topic`
- `agent_response_topic`
- Any additional runtime topics specified in worker configs

## 🧪 Development

### Adding New Message Types

1. **Define in `events.py`**:
   ```python
   @dataclass
   class CustomRequest(KafkaMessageType):
       field1: str
       field2: int
   ```

2. **Update agent configuration** to use new types
3. **Modify Flink SQL** to process new message structure

### Adding New Workers

1. **Create new config file**: `config_worker3.yml`
2. **Update main.py** to instantiate additional runtime
3. **Deploy corresponding Flink job** if needed

### Debugging

Enable detailed logging:
```python
# When prompted, choose 'Y' for logging
# Or set programmatically:
logging.basicConfig(level=logging.DEBUG)
```

Debug information includes:
- Kafka connection status
- Message serialization/deserialization
- Agent lifecycle events
- Schema Registry interactions

## 📚 Dependencies

Core dependencies (managed via `pyproject.toml`):
- `autogen-kafka-extension` - Core Kafka agent functionality
- `autogen-core` - Base agent framework
- `aiorun` - Async application runner

## 🔗 Related Documentation

- **[Parent README](../README.md)** - Overall sample documentation
- **[Main Project README](../../../../README.md)** - Project overview
- **[Confluent Cloud Docs](https://docs.confluent.io/cloud/)** - Kafka setup
- **[Flink SQL Reference](https://docs.confluent.io/cloud/current/flink/)** - SQL job development

## 🤝 Contributing

When modifying this sample:

1. **Test both runtime configurations** (worker1 and worker2)
2. **Verify Flink SQL compatibility** with message schema changes
3. **Update configuration documentation** for new fields
4. **Test end-to-end flow** from input to Flink processing to response
5. **Handle errors gracefully** with proper logging

## 🐛 Troubleshooting

### Common Issues

1. **Topic Not Found**:
   - Verify topics exist in Confluent Cloud
   - Check topic names match configuration exactly

2. **Authentication Failures**:
   - Validate API keys are active
   - Ensure Schema Registry credentials are correct

3. **Flink Job Issues**:
   - Check job is deployed and running
   - Verify OpenAI connection is configured
   - Monitor Flink logs for processing errors

4. **Message Processing Delays**:
   - Check consumer lag in Confluent Cloud
   - Verify Flink job throughput
   - Monitor OpenAI API rate limits

5. **Schema Registry Errors**:
   - Ensure schemas are properly registered
   - Check schema compatibility settings
   - Verify message serialization format

For detailed troubleshooting, enable debug logging and monitor Confluent Cloud metrics. 
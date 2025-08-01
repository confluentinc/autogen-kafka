# Developer Guide - AutoGen Kafka Extension

This guide provides comprehensive information for developers working on or extending the AutoGen Kafka Extension.

## 🏗️ Development Setup

### Prerequisites
- Python 3.10 or higher
- Apache Kafka (Docker Compose provided)
- Schema Registry
- Poetry or uv for dependency management

### Getting Started
```bash
# Clone the repository
git clone https://github.com/microsoft/autogen-kafka.git
cd autogen-kafka/python/packages/autogen-kafka-extension

# Install dependencies
uv pip install -e .[dev]
# or
poetry install --with dev

# Start Kafka infrastructure
cd ../../../../
docker-compose up -d
```

## 📐 Architecture Deep Dive

### Core Design Principles

1. **Event-Driven Architecture**: All communication flows through Kafka topics
2. **Service Separation**: Clear boundaries between runtime, agents, and services
3. **Type Safety**: Strong typing with runtime validation
4. **Observability**: Built-in tracing and metrics
5. **Fault Tolerance**: Graceful degradation and error recovery

### Component Interaction Patterns

#### Agent Lifecycle
```python
# Registration Pattern
factory = lambda: MyAgent()
agent_type = await runtime.register_factory("my_agent", factory)
agent_id = AgentId("my_agent", "instance_1")

# Message Processing Pattern
async def on_message_impl(self, message, ctx):
    # 1. Validate input
    # 2. Process business logic
    # 3. Return response/None
    return response
```

#### Service Integration Pattern
```python
class MyService:
    def __init__(self, config, streaming_service):
        self._config = config
        self._streaming_service = streaming_service
        
    async def start(self):
        # Initialize resources
        pass
        
    async def stop(self):
        # Cleanup resources
        pass
```

### Configuration System

#### Adding New Configuration Classes

```python
from autogen_kafka.config.base_config import BaseConfig
from autogen_kafka.config.auto_validate import auto_validate_after_init


@auto_validate_after_init
class MyServiceConfig(BaseConfig):
    def __init__(self, setting1: str, setting2: int = 42):
        super().__init__()
        self._setting1 = setting1
        self._setting2 = setting2

    def _validate_impl(self) -> ValidationResult:
        errors = []
        warnings = []

        if not self._setting1:
            errors.append("setting1 cannot be empty")

        if self._setting2 < 0:
            warnings.append("setting2 should be positive")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
```

## 🧪 Testing Guidelines

### Unit Testing
```python
import pytest
from unittest.mock import AsyncMock, Mock

class TestMyComponent:
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.setting = "test_value"
        return config
    
    @pytest.mark.asyncio
    async def test_async_method(self, mock_config):
        component = MyComponent(mock_config)
        result = await component.process()
        assert result == expected_value
```

### Integration Testing
```python
@pytest.mark.integration
class TestKafkaIntegration:
    @pytest.fixture(scope="class")
    async def kafka_cluster(self):
        # Set up test Kafka cluster
        yield cluster
        # Teardown
    
    async def test_end_to_end_flow(self, kafka_cluster):
        # Test actual Kafka integration
        pass
```

### Test Utilities
```python
# tests/utils.py
async def create_test_runtime(config_overrides=None):
    """Helper to create test runtime with mocked dependencies."""
    config = create_test_config(config_overrides)
    runtime = KafkaWorkerAgentRuntime(config)
    return runtime

def create_test_message(message_type="TestMessage", data=None):
    """Helper to create test messages."""
    return {
        "type": message_type,
        "data": data or {"test": "data"}
    }
```

## 🔧 Extension Points

### Custom Event Types

```python
from autogen_kafka.shared.events.event_base import EventBase


class CustomEvent(EventBase):
    def __init__(self, custom_field: str, timestamp: float):
        self.custom_field = custom_field
        self.timestamp = timestamp

    @classmethod
    def __schema__(cls) -> str:
        return json.dumps({
            "type": "object",
            "properties": {
                "custom_field": {"type": "string"},
                "timestamp": {"type": "number"}
            },
            "required": ["custom_field", "timestamp"]
        })
```

### Custom Serializers

```python
from autogen_kafka.shared.events.events_serdes import EventSerializer


class CustomSerializer(EventSerializer):
    async def serialize(self, payload, headers=None, serializer_kwargs=None):
        # Custom serialization logic
        return custom_serialized_data
```

### Custom Services

```python
from autogen_kafka.shared.streaming_worker_base import StreamingWorkerBase


class CustomService(StreamingWorkerBase):
    def __init__(self, config):
        super().__init__(config, "custom.topic", CustomEvent)

    async def _handle_event(self, record, stream, send):
        # Custom event handling logic
        pass
```

## 📊 Monitoring & Debugging

### Logging Setup
```python
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Component-specific loggers
logger = logging.getLogger(__name__)
```

### Tracing Integration
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def my_method(self):
    with tracer.start_as_current_span("my_method") as span:
        span.set_attribute("component", "my_service")
        # Method implementation
```

### Metrics Collection
```python
from prometheus_client import Counter, Histogram

message_counter = Counter('messages_processed_total', 'Total processed messages')
processing_time = Histogram('message_processing_seconds', 'Message processing time')

async def process_message(self, message):
    with processing_time.time():
        # Process message
        message_counter.inc()
```

## 🔒 Security Considerations

### Kafka Security
```python
kafka_config = KafkaConfig(
    bootstrap_servers=["secure-kafka:9093"],
    security_protocol="SASL_SSL",
    sasl_mechanism="PLAIN",
    sasl_username="user",
    sasl_password="password",
    ssl_cafile="/path/to/ca.pem"
)
```

### Input Validation
```python
def validate_message(message):
    if not isinstance(message, dict):
        raise ValueError("Message must be a dictionary")
    
    required_fields = ["type", "data"]
    for field in required_fields:
        if field not in message:
            raise ValueError(f"Missing required field: {field}")
```

## 🚀 Performance Optimization

### Connection Pooling
```python
# Use connection pooling for high-throughput scenarios
kafka_config = KafkaConfig(
    bootstrap_servers=["kafka:9092"],
    producer_config={
        "linger.ms": 5,
        "batch.size": 16384,
        "acks": 1
    },
    consumer_config={
        "fetch.min.bytes": 1024,
        "fetch.max.wait.ms": 500
    }
)
```

### Batch Processing
```python
async def process_batch(self, messages):
    # Process messages in batches for better throughput
    batch_size = 100
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i + batch_size]
        await self.process_message_batch(batch)
```

## 🐛 Common Pitfalls & Solutions

### 1. Agent State Management
**Problem**: Agent state not persisting across restarts
**Solution**: Implement save_state/load_state methods properly

### 2. Message Ordering
**Problem**: Messages processed out of order
**Solution**: Use single partition or implement ordering logic

### 3. Memory Leaks
**Problem**: Pending requests accumulating
**Solution**: Implement proper cleanup in close() methods

### 4. Serialization Issues
**Problem**: Type mismatches during deserialization
**Solution**: Ensure schema compatibility and proper type registration

## 📋 Code Review Checklist

- [ ] All async methods have proper error handling
- [ ] Resources are properly cleaned up (connections, tasks)
- [ ] Configuration classes have validation
- [ ] New components have comprehensive tests
- [ ] Documentation is updated for API changes
- [ ] Logging statements are informative but not verbose
- [ ] Type hints are complete and accurate
- [ ] Security considerations are addressed
- [ ] Performance impact is minimal

## 🔄 Release Process

### Version Bumping
```bash
# Update version in pyproject.toml
# Update CHANGELOG.md
# Create release PR
# Tag after merge
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3
```

### Documentation Updates
- Update API documentation for breaking changes
- Add migration guide for major versions
- Update examples and tutorials

## 🤝 Contributing Guidelines

1. **Fork and Clone**: Fork the repository and clone your fork
2. **Branch**: Create a feature branch from main
3. **Develop**: Make changes following the coding standards
4. **Test**: Ensure all tests pass and add new tests for new features
5. **Document**: Update documentation as needed
6. **PR**: Submit a pull request with clear description

### Coding Standards
- Use type hints for all public APIs
- Follow PEP 8 style guidelines
- Write comprehensive docstrings
- Include examples in documentation
- Handle errors gracefully
- Use async/await consistently

---

For questions or clarification, please open an issue or reach out to the maintainers. 
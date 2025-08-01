# Troubleshooting Guide - AutoGen Kafka Extension

This guide helps diagnose and resolve common issues when working with the AutoGen Kafka Extension.

## 🔧 Quick Diagnostics

### Health Check Commands
```bash
# Check Kafka connectivity
kafka-topics --bootstrap-server localhost:9092 --list

# Check Schema Registry
curl http://localhost:8081/subjects

# Check consumer groups
kafka-consumer-groups --bootstrap-server localhost:9092 --list

# Check topic details
kafka-topics --bootstrap-server localhost:9092 --describe --topic agent.requests
```

### Python Health Check

```python
import asyncio
from autogen_kafka import KafkaConfig


async def health_check():
    config = KafkaConfig(bootstrap_servers=["localhost:9092"])
    try:
        # Test connection
        backend = config.get_kafka_backend()
        print("✅ Kafka connection successful")
    except Exception as e:
        print(f"❌ Kafka connection failed: {e}")


asyncio.run(health_check())
```

## 🚨 Common Issues & Solutions

### Connection Issues

#### Issue: "No brokers available"
**Symptoms:**
- RuntimeError: "No brokers available"
- Connection timeouts
- Agent startup failures

**Causes & Solutions:**
1. **Kafka not running**
   ```bash
   # Check if Kafka is running
   docker ps | grep kafka
   
   # Start Kafka if needed
   docker-compose up -d kafka
   ```

2. **Wrong bootstrap servers**
   ```python
   # ❌ Wrong
   config = KafkaConfig(bootstrap_servers=["kafka:9092"])
   
   # ✅ Correct for local development
   config = KafkaConfig(bootstrap_servers=["localhost:9092"])
   ```

3. **Network connectivity issues**
   ```bash
   # Test connectivity
   nc -zv localhost 9092
   
   # Check Docker network
   docker network ls
   docker network inspect autogen-kafka_default
   ```

#### Issue: "Schema Registry unreachable"
**Symptoms:**
- Schema validation errors
- Serialization failures
- Registry connection timeouts

**Solutions:**
1. **Check Schema Registry status**
   ```bash
   curl -f http://localhost:8081/subjects || echo "Registry unavailable"
   ```

2. **Verify configuration**
   ```python
   config = KafkaConfig(
       bootstrap_servers=["localhost:9092"],
       schema_registry={"url": "http://localhost:8081"}  # ✅ Correct URL
   )
   ```

### Agent Issues

#### Issue: "Agent not found"
**Symptoms:**
- ValueError: "Agent with name X not found"
- Messages not reaching agents
- Agent registration failures

**Debugging Steps:**
1. **Check agent registration**
   ```python
   # List registered agents
   print(f"Registered agents: {list(runtime._agent_manager._agent_factories.keys())}")
   
   # Check agent instance
   agent_id = AgentId("my_agent", "instance_1")
   try:
       agent = await runtime._agent_manager.get_agent(agent_id)
       print(f"✅ Agent found: {agent}")
   except Exception as e:
       print(f"❌ Agent not found: {e}")
   ```

2. **Verify agent type consistency**
   ```python
   # ❌ Wrong - type mismatch
   await runtime.register_factory("chat_agent", lambda: ChatBot())
   agent_id = AgentId("chatbot", "1")  # Different type name!
   
   # ✅ Correct - consistent naming
   await runtime.register_factory("chat_agent", lambda: ChatBot())
   agent_id = AgentId("chat_agent", "1")
   ```

#### Issue: "Agent not responding"
**Symptoms:**
- Messages sent but no response
- Timeouts on agent calls
- Deadlocks

**Debugging:**
1. **Check agent implementation**
   ```python
   class MyAgent(BaseAgent):
       async def on_message_impl(self, message, ctx):
           # ❌ Wrong - blocking operation
           time.sleep(10)
           
           # ✅ Correct - async operation
           await asyncio.sleep(0.1)
           return "response"
   ```

2. **Enable debug logging**
   ```python
   import logging
   logging.getLogger('autogen_kafka_extension').setLevel(logging.DEBUG)
   ```

3. **Check message context**
   ```python
   async def on_message_impl(self, message, ctx):
       print(f"Received message: {message}")
       print(f"Context: sender={ctx.sender}, is_rpc={ctx.is_rpc}")
       return "processed"
   ```

### Serialization Issues

#### Issue: "Serialization failed"
**Symptoms:**
- ValueError during message serialization
- Type mismatch errors
- Schema validation failures

**Solutions:**
1. **Check message types**
   ```python
   # ❌ Wrong - unregistered type
   await runtime.send_message({"data": "test"}, agent_id)
   
   # ✅ Correct - registered type
   from dataclasses import dataclass
   
   @dataclass
   class MyMessage:
       data: str
   
   message = MyMessage(data="test")
   await runtime.send_message(message, agent_id)
   ```

2. **Verify schema compatibility**
   ```python
   # Check if type is registered
   registry = runtime._serialization_registry
   type_name = registry.type_name(message)
   is_registered = registry.is_registered(type_name, JSON_DATA_CONTENT_TYPE)
   print(f"Type {type_name} registered: {is_registered}")
   ```

### Memory Issues

#### Issue: "Memory leaks"
**Symptoms:**
- Increasing memory usage over time
- Pending requests accumulating
- OOM errors

**Solutions:**
1. **Check pending requests cleanup**
   ```python
   # Monitor pending requests
   print(f"Pending requests: {len(agent._pending_requests)}")
   
   # Ensure proper cleanup
   async def close(self):
       async with self._pending_requests_lock:
           for future in self._pending_requests.values():
               if not future.done():
                   future.cancel()
           self._pending_requests.clear()
   ```

2. **Monitor background tasks**
   ```python
   # Check background tasks
   print(f"Background tasks: {len(task_manager._background_tasks)}")
   
   # Ensure proper cleanup
   await task_manager.wait_for_completion()
   ```

### Performance Issues

#### Issue: "High latency"
**Symptoms:**
- Slow message processing
- High response times
- Throughput bottlenecks

**Optimization:**
1. **Kafka configuration tuning**
   ```python
   config = KafkaConfig(
       bootstrap_servers=["localhost:9092"],
       producer_config={
           "linger.ms": 5,        # Batch messages
           "batch.size": 16384,   # Larger batches
           "acks": 1,             # Faster acknowledgment
           "compression.type": "snappy"  # Compression
       },
       consumer_config={
           "fetch.min.bytes": 1024,      # Minimize fetches
           "fetch.max.wait.ms": 500,     # Reduce wait time
           "max.poll.records": 500       # Process more records
       }
   )
   ```

2. **Agent optimization**
   ```python
   class OptimizedAgent(BaseAgent):
       async def on_message_impl(self, message, ctx):
           # ❌ Slow - synchronous processing
           result = process_synchronously(message)
           
           # ✅ Fast - async processing
           result = await process_asynchronously(message)
           return result
   ```

## 🔍 Debugging Tools

### Logging Configuration
```python
import logging
import sys

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kafka_extension.log')
    ]
)

# Component-specific logging
logging.getLogger('autogen_kafka_extension.agent').setLevel(logging.DEBUG)
logging.getLogger('autogen_kafka_extension.runtimes').setLevel(logging.INFO)
logging.getLogger('kstreams').setLevel(logging.WARNING)
```

### Message Tracing
```python
class TracingAgent(BaseAgent):
    async def on_message_impl(self, message, ctx):
        print(f"🔍 TRACE: Received message")
        print(f"   Type: {type(message)}")
        print(f"   Content: {message}")
        print(f"   Sender: {ctx.sender}")
        print(f"   Message ID: {ctx.message_id}")
        print(f"   Is RPC: {ctx.is_rpc}")
        
        response = await self.process_message(message)
        
        print(f"🔍 TRACE: Sending response")
        print(f"   Type: {type(response)}")
        print(f"   Content: {response}")
        
        return response
```

### Performance Monitoring
```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            print(f"⏱️ {func.__name__} took {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {func.__name__} failed after {duration:.3f}s: {e}")
            raise
    return wrapper

class MonitoredAgent(BaseAgent):
    @monitor_performance
    async def on_message_impl(self, message, ctx):
        # Your processing logic
        return response
```

## 📊 Monitoring & Metrics

### Essential Metrics to Track
```python
from prometheus_client import Counter, Histogram, Gauge

# Message metrics
messages_received = Counter('messages_received_total', 'Total messages received')
messages_processed = Counter('messages_processed_total', 'Total messages processed')
message_processing_time = Histogram('message_processing_seconds', 'Message processing time')

# Agent metrics
active_agents = Gauge('active_agents', 'Number of active agents')
pending_requests = Gauge('pending_requests', 'Number of pending requests')

# Kafka metrics
kafka_connection_errors = Counter('kafka_connection_errors_total', 'Kafka connection errors')

# Usage in agent
class MetricsAgent(BaseAgent):
    async def on_message_impl(self, message, ctx):
        messages_received.inc()
        with message_processing_time.time():
            result = await self.process(message)
            messages_processed.inc()
            return result
```

### Health Check Endpoint
```python
from aiohttp import web
import json

async def health_check(request):
    status = {
        "status": "healthy",
        "kafka": await check_kafka_health(),
        "schema_registry": await check_schema_registry_health(),
        "agents": await check_agents_health()
    }
    
    status_code = 200 if all(status.values()) else 503
    return web.Response(
        text=json.dumps(status),
        status=status_code,
        content_type='application/json'
    )

app = web.Application()
app.router.add_get('/health', health_check)
```

## 🆘 Getting Help

### Before Opening an Issue
1. Check this troubleshooting guide
2. Enable debug logging and capture logs
3. Try to create a minimal reproduction case
4. Check if the issue exists in the latest version

### Information to Include
- Python version and environment
- AutoGen Kafka Extension version
- Kafka version and configuration
- Full error traceback
- Minimal code to reproduce the issue
- Relevant logs with timestamps

### Community Resources
- GitHub Issues: For bugs and feature requests
- Documentation: For API reference and guides
- Examples: For common usage patterns

---

If you can't find a solution here, please open an issue with the requested information. 
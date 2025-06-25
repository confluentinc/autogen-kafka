#!/bin/bash

PYTHONPATH=tests:src uv run python -m pytest tests/test_worker_runtime.py tests/test_kafka_memory.py tests/test_kafka_streaming_agent.py tests/test_cloudevent_schema.py tests/test_schema_registry.py -v

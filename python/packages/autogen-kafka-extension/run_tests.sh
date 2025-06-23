#!/bin/bash

PYTHONPATH=tests:src uv run python -m pytest tests/test_worker_runtime.py tests/test_kafka_memory.py tests/test_kafka_streaming_agent.py -v

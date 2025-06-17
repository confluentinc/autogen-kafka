#!/bin/bash

PYTHONPATH=tests:src uv run python -m pytest tests/test_worker_runtime.py

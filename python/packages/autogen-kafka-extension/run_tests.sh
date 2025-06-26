#!/bin/bash

# If the user specified a specific test file, run only that file
if [ $# -eq 1 ]; then
    TEST_FILE=$1
    PYTHONPATH=tests:src uv run python -m pytest $TEST_FILE -v
    exit 0
fi

PYTHONPATH=tests:src uv run python -m pytest tests/ -v

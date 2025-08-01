"""Shared package for autogen-kafka-extension.

This package provides shared utilities, services, and base classes used across
the extension components.
"""
from .message_producer import MessageProducer
from .streaming_service import StreamingService
from .streaming_worker_base import StreamingWorkerBase
from .background_task_manager import BackgroundTaskManager

__all__ = [
    "StreamingService",
    "StreamingWorkerBase", 
    "BackgroundTaskManager",
    "MessageProducer"
]

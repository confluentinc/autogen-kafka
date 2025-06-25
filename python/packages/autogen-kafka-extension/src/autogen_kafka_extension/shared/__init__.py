"""Shared package for autogen-kafka-extension.

This package provides shared utilities, services, and base classes used across
the extension components.
"""
from .streaming_service import StreamingService
from .streaming_worker_base import StreamingWorkerBase
from .topic_admin_service import TopicAdminService
from .background_task_manager import BackgroundTaskManager

__all__ = [
    "StreamingService",
    "StreamingWorkerBase", 
    "TopicAdminService",
    "BackgroundTaskManager",
]

import asyncio
import logging
import time
from asyncio import Task
from typing import Any, Coroutine, Set

logger = logging.getLogger(__name__)


def _raise_on_exception(task: Task[Any]) -> None:
    exception = task.exception()
    if exception is not None:
        logger.error("Error in background task", exc_info=exception)
        raise exception


class BackgroundTaskManager:
    """Manages background tasks with concurrency limits and detailed logging."""

    def __init__(self, max_concurrency: int = 100, enable_logging: bool = True):
        """
        Args:
            max_concurrency: Maximum number of concurrent tasks.
            enable_logging: Whether to log task metrics and queue status.
        """
        self._background_tasks: Set[Task[Any]] = set()
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._max_concurrency = max_concurrency
        self._enable_logging = enable_logging
        self._active_task_count = 0
        self._task_lock = asyncio.Lock()

    def add_task(self, coro: Coroutine[Any, Any, Any], name: str = "unnamed") -> None:
        """Add a coroutine to be run as a background task with concurrency control."""

        async def wrapper():
            async with self._semaphore:
                start_time = time.perf_counter()
                await self._increment_active()
                try:
                    if self._enable_logging:
                        logger.debug(f"[TaskManager] Task '{name}' started. Active: {self._active_task_count}")
                    await coro
                finally:
                    duration = time.perf_counter() - start_time
                    await self._decrement_active()
                    if self._enable_logging:
                        logger.debug(f"[TaskManager] Task '{name}' completed in {duration:.4f}s. "
                                     f"Active: {self._active_task_count}")

        task = asyncio.create_task(wrapper())
        self._background_tasks.add(task)
        task.add_done_callback(_raise_on_exception)
        task.add_done_callback(self._background_tasks.discard)

    async def _increment_active(self):
        async with self._task_lock:
            self._active_task_count += 1

    async def _decrement_active(self):
        async with self._task_lock:
            self._active_task_count -= 1

    async def wait_for_completion(self) -> None:
        """Wait for all background tasks to finish."""
        if not self._background_tasks:
            return

        logger.info("[TaskManager] Waiting for all background tasks to complete...")
        final_results = await asyncio.gather(*self._background_tasks, return_exceptions=True)

        for result in final_results:
            if isinstance(result, Exception):
                logger.error("Error in background task", exc_info=result)

        logger.info("[TaskManager] All background tasks completed.")
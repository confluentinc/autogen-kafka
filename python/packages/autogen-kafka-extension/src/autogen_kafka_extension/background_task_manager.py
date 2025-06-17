import asyncio
import logging
from asyncio import Task
from typing import Any, Awaitable, Set

logger = logging.getLogger(__name__)


def _raise_on_exception(task: Task[Any]) -> None:
    """Helper function to raise exceptions from background tasks."""
    exception = task.exception()
    if exception is not None:
        raise exception


class BackgroundTaskManager:
    """Manages background tasks and their lifecycle."""
    
    def __init__(self):
        self._background_tasks: Set[Task[Any]] = set()
    
    def add_task(self, coro: Awaitable[Any]) -> None:
        """Add a coroutine as a background task and track its completion."""
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(_raise_on_exception)
        task.add_done_callback(self._background_tasks.discard)
    
    async def wait_for_completion(self) -> None:
        """Wait for all background tasks to complete."""
        if not self._background_tasks:
            return
            
        final_tasks_results = await asyncio.gather(*self._background_tasks, return_exceptions=True)
        for task_result in final_tasks_results:
            if isinstance(task_result, Exception):
                logger.error("Error in background task", exc_info=task_result) 
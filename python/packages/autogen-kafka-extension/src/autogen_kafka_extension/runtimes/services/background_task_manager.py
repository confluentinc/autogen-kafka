import asyncio
import logging
from asyncio import Task
from typing import Any, Coroutine, Set

logger = logging.getLogger(__name__)


def _raise_on_exception(task: Task[Any]) -> None:
    """
    Helper function to raise exceptions from background tasks.
    
    This callback function is attached to background tasks to ensure that any
    exceptions that occur during task execution are properly raised and not
    silently ignored.
    
    Args:
        task: The completed asyncio Task to check for exceptions.
        
    Raises:
        Exception: Any exception that occurred during the task execution.
    """
    exception = task.exception()
    if exception is not None:
        raise exception


class BackgroundTaskManager:
    """Manages background tasks and their lifecycle."""
    
    def __init__(self):
        """
        Initialize the BackgroundTaskManager.
        
        Creates an empty set to track all background tasks that are currently
        running or scheduled to run.
        """
        self._background_tasks: Set[Task[Any]] = set()
    
    def add_task(self, coro: Coroutine[Any, Any, Any]) -> None:
        """
        Add a coroutine as a background task and track its completion.
        
        Creates an asyncio task from the provided coroutine and adds it to the
        internal tracking set. The task will automatically remove itself from
        the tracking set when it completes, and any exceptions will be raised
        through the done callback.
        
        Args:
            coro: The coroutine to run as a background task. Must be a coroutine
                 object (not just any awaitable).
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(_raise_on_exception)
        task.add_done_callback(self._background_tasks.discard)
    
    async def wait_for_completion(self) -> None:
        """
        Wait for all background tasks to complete.
        
        This method will block until all currently tracked background tasks
        have finished executing. If any tasks raise exceptions, those exceptions
        will be logged as errors but will not prevent other tasks from completing.
        
        Returns:
            None: This method doesn't return any value, it just waits for completion.
            
        Note:
            If there are no background tasks currently running, this method
            returns immediately without waiting.
        """
        if not self._background_tasks:
            return
            
        final_tasks_results = await asyncio.gather(*self._background_tasks, return_exceptions=True)
        for task_result in final_tasks_results:
            if isinstance(task_result, Exception):
                logger.error("Error in background task", exc_info=task_result) 
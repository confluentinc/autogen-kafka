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
        """Add a coroutine as a background task and track its completion.
        
        This method provides fire-and-forget task execution with proper error
        handling and lifecycle management. The task is automatically tracked
        and cleaned up when it completes.
        
        Key behaviors:
        - Task is immediately scheduled for execution
        - Exceptions are propagated via the done callback (preventing silent failures)
        - Task automatically removes itself from tracking when complete
        - Multiple tasks can be added and will run concurrently
        
        Args:
            coro: The coroutine to run as a background task. Must be a proper
                 coroutine object (created with async def or async generator),
                 not just any awaitable like a Future or Task.
                
        Raises:
            TypeError: If coro is not a coroutine object
            RuntimeError: If called from outside an asyncio event loop context
            
        Example:
            ```python
            async def send_notification(message: str):
                await kafka_producer.send("notifications", message)
            
            task_manager = BackgroundTaskManager()
            task_manager.add_task(send_notification("Hello World"))
            ```
            
        Note:
            Tasks added via this method will continue running even if the original
            caller completes. Use wait_for_completion() to ensure all tasks finish
            before shutting down.
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(_raise_on_exception)
        task.add_done_callback(self._background_tasks.discard)
    
    async def wait_for_completion(self) -> None:
        """Wait for all background tasks to complete with proper error handling.
        
        This method provides graceful shutdown capabilities by ensuring all
        background tasks finish before the application terminates. It uses
        asyncio.gather with return_exceptions=True to handle task failures
        gracefully without interrupting other tasks.
        
        Behavior:
        - Waits for all currently tracked tasks (snapshot at call time)
        - New tasks added during waiting are not included
        - Exceptions from individual tasks are logged but don't stop waiting
        - Method completes only when all tasks finish (success or failure)
        - Returns immediately if no tasks are currently tracked
        
        Returns:
            None: This method provides synchronization only, no return value
            
        Example:
            ```python
            # Add several background tasks
            for i in range(10):
                task_manager.add_task(process_item(i))
            
            # Wait for all to complete before shutdown
            await task_manager.wait_for_completion()
            print("All background tasks completed")
            ```
            
        Note:
            This method captures a snapshot of current tasks and waits only for those.
            Tasks added after this method is called will not be awaited. For complete
            shutdown, call this method when no new tasks will be added.
            
        Logging:
            Task exceptions are logged at ERROR level with full traceback for
            debugging purposes, but do not prevent successful completion of the
            wait operation.
        """
        if not self._background_tasks:
            return
            
        final_tasks_results = await asyncio.gather(*self._background_tasks, return_exceptions=True)
        for task_result in final_tasks_results:
            if isinstance(task_result, Exception):
                logger.error("Error in background task", exc_info=task_result) 
import asyncio
import logging
import time
from typing import Union, Callable, Awaitable

logger = logging.getLogger(__name__)

class Helpers:

    @staticmethod
    async def wait_for_condition(
            check_func: Union[Callable[[], bool], Callable[[], Awaitable[bool]]],
            *,
            timeout: float,
            check_interval: float = 0.5,
            expected: bool = True
    ) -> bool:
        """
        Waits until `check_func()` returns the expected value or until timeout.

        Args:
            check_func: A function (sync or async) that returns a boolean.
            timeout: Maximum time in seconds to wait.
            check_interval: Time between checks in seconds.
            expected: The value to wait for (True by default).

        Returns:
            True if condition met within timeout, False otherwise.
        """

        if timeout < 0:
            raise ValueError("Timeout must be non-negative")
        if check_interval <= 0:
            raise ValueError("Check interval must be positive")

        start_time = time.monotonic()

        while True:
            result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
            if result == expected:
                return True

            elapsed = time.monotonic() - start_time
            if elapsed >= timeout:
                result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                if result == expected:
                    return True
                else:
                    logger.warning(
                        f"Timeout waiting after {timeout}s. "
                    )
                    return False

            await asyncio.sleep(0.1)
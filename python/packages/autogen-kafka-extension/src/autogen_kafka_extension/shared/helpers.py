import asyncio
from typing import Union, Callable, Awaitable


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

        async def _check():
            while True:
                result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                if result == expected:
                    return True
                await asyncio.sleep(check_interval)

        try:
            return await asyncio.wait_for(_check(), timeout)
        except asyncio.TimeoutError:
            return False
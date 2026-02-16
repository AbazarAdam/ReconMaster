from typing import Any
import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """A token-bucket based rate limiter for controlling request frequency.

    Ensures that modules do not exceed API limits or overwhelm target servers
    by enforcing a maximum number of operations per second.

    Attributes:
        rate: The number of tokens added per second.
        capacity: The maximum number of tokens the bucket can hold.
        tokens: The current number of available tokens.
        last_update: Timestamp of the last token replenishment.
        lock: Asyncio lock to ensure thread-safe token acquisition.
    """

    def __init__(self, rate_per_second: float):
        """Initializes the limiter with a specific rate.

        Args:
            rate_per_second: Tokens (requests) permitted per second.
        """
        self.rate = rate_per_second
        self.capacity = rate_per_second
        self.tokens = rate_per_second
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquires a single token, blocking until one is available.

        Uses the token bucket algorithm to replenish tokens based on elapsed
        time since the last acquisition.
        """
        if self.rate <= 0:
            return

        async with self.lock:
            while self.tokens < 1:
                now = time.monotonic()
                elapsed = now - self.last_update
                # Replenish tokens based on time passed
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now

                if self.tokens < 1:
                    # Calculate wait time for the next token to become available
                    wait_time = (1 - self.tokens) / self.rate
                    await asyncio.sleep(wait_time)

            self.tokens -= 1
            logger.debug("[LIMITER] Token acquired successfully")

    async def __aenter__(self) -> "RateLimiter":
        """Async context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        pass

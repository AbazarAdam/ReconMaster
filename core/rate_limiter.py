import asyncio
import time
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    A token bucket rate limiter to control the frequency of requests.
    """
    def __init__(self, rate_per_second: float):
        self.rate = rate_per_second
        self.capacity = rate_per_second
        self.tokens = rate_per_second
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """
        Acquires a token, waiting if necessary.
        """
        if self.rate <= 0:
            return

        async with self.lock:
            while self.tokens < 1:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                if self.tokens < 1:
                    wait_time = (1 - self.tokens) / self.rate
                    await asyncio.sleep(wait_time)
            
            self.tokens -= 1
            logger.debug("Token acquired")

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

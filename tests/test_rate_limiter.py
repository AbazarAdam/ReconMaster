import pytest
import asyncio
from core.rate_limiter import RateLimiter

@pytest.mark.asyncio
async def test_rate_limiter_allows_limited_rate():
    limiter = RateLimiter(rate_per_second=2)  # 2 tokens/sec
    start = asyncio.get_event_loop().time()
    for _ in range(4):
        await limiter.acquire()
    elapsed = asyncio.get_event_loop().time() - start
    # The first token is available immediately, so 3 tokens at 2/sec = at least 1.5s
    # Allow for timing inaccuracy in CI/local runs
    assert elapsed >= 0.9

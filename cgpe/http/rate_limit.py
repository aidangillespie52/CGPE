# cgpe/http/rate_limit.py

import asyncio
import random
import time
from dataclasses import dataclass


@dataclass
class RateLimiter:
    rps: float = 1.0
    jitter_s: float = 0.20

    def __post_init__(self) -> None:
        if self.rps <= 0:
            raise ValueError("rps must be > 0")
        if self.jitter_s < 0:
            raise ValueError("jitter_s must be >= 0")

        self._min_interval = 1.0 / self.rps
        self._lock = asyncio.Lock()
        self._next_time = 0.0  # monotonic timestamp

    async def wait(self) -> None:
        """
        Await until you're allowed to make the next request.
        """
        async with self._lock:
            now = time.monotonic()
            if now < self._next_time:
                await asyncio.sleep(self._next_time - now)

            # schedule next slot + a bit of jitter
            self._next_time = (
                time.monotonic()
                + self._min_interval
                + random.uniform(0.0, self.jitter_s)
            )


def backoff_seconds(attempt: int, *, base: float = 1.0, cap: float = 60.0) -> float:
    return min(cap, base * (2 ** attempt) + random.uniform(0.0, 1.5))


# Global shared limiter (import this everywhere you do HTTP)
RATE_LIMITER = RateLimiter(rps=0.25, jitter_s=0.10)

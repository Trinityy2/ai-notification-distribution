import time
from collections import deque

from app.security.rate_limiting.base import RateLimiter, RateLimitExceeded


class InMemoryRateLimiter(RateLimiter):
    """Sliding-window rate limiter backed by in-process memory.

    Suitable for single-instance deployments and tests.
    For multi-instance deployments, use a Redis-backed implementation.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._windows: dict[str, deque[float]] = {}

    async def check(self, identifier: str) -> None:
        now = time.monotonic()
        cutoff = now - self._window

        if identifier not in self._windows:
            self._windows[identifier] = deque()

        window = self._windows[identifier]
        # Drop timestamps outside the current window
        while window and window[0] <= cutoff:
            window.popleft()

        if len(window) >= self._max:
            raise RateLimitExceeded(
                f"Rate limit of {self._max} req/{self._window}s exceeded."
            )

        window.append(now)

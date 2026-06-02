from abc import ABC, abstractmethod


class RateLimitExceeded(Exception):
    """Raised when a key exceeds its allowed request rate."""


class RateLimiter(ABC):
    @abstractmethod
    async def check(self, identifier: str) -> None:
        """Raise RateLimitExceeded if *identifier* has exceeded the limit."""

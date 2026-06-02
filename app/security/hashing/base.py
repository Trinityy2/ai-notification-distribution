from abc import ABC, abstractmethod


class KeyHasher(ABC):
    """Abstract hasher for API keys.

    SHA-256 is recommended for API keys (deterministic lookup).
    BCrypt is available but requires iterating all keys for verification.
    """

    @abstractmethod
    def hash(self, raw_key: str) -> str:
        """Return a hex digest of *raw_key*."""

    @abstractmethod
    def verify(self, raw_key: str, hashed: str) -> bool:
        """Return True if *raw_key* matches *hashed*."""

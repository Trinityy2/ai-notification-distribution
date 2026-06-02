import pytest

from app.security.hashing.sha256 import SHA256KeyHasher
from app.security.hashing.bcrypt import BcryptKeyHasher
from app.security.hashing.base import KeyHasher


class _HasherContract:
    """Shared contract tests run against every KeyHasher implementation."""

    hasher: KeyHasher

    def test_hash_returns_string(self):
        result = self.hasher.hash("my-api-key")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_verify_correct_key_returns_true(self):
        raw = "super-secret-key-123"
        hashed = self.hasher.hash(raw)
        assert self.hasher.verify(raw, hashed) is True

    def test_verify_wrong_key_returns_false(self):
        hashed = self.hasher.hash("correct-key")
        assert self.hasher.verify("wrong-key", hashed) is False

    def test_empty_string_is_hashable(self):
        hashed = self.hasher.hash("")
        assert self.hasher.verify("", hashed) is True
        assert self.hasher.verify("not-empty", hashed) is False


class TestSHA256KeyHasher(_HasherContract):
    hasher = SHA256KeyHasher(secret="test-secret")

    def test_is_deterministic(self):
        """Same input must always produce the same hash (needed for DB lookup)."""
        raw = "deterministic-key"
        assert self.hasher.hash(raw) == self.hasher.hash(raw)

    def test_different_secrets_produce_different_hashes(self):
        h1 = SHA256KeyHasher(secret="secret-a")
        h2 = SHA256KeyHasher(secret="secret-b")
        assert h1.hash("same-key") != h2.hash("same-key")

    def test_different_secrets_cross_verify_fails(self):
        h1 = SHA256KeyHasher(secret="secret-a")
        h2 = SHA256KeyHasher(secret="secret-b")
        hashed = h1.hash("key")
        assert h2.verify("key", hashed) is False


class TestBcryptKeyHasher(_HasherContract):
    hasher = BcryptKeyHasher(rounds=4)  # low rounds for test speed

    def test_is_non_deterministic(self):
        """BCrypt uses a random salt, so two hashes of the same key differ."""
        raw = "non-deterministic-key"
        assert self.hasher.hash(raw) != self.hasher.hash(raw)

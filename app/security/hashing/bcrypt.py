import bcrypt

from app.security.hashing.base import KeyHasher


class BcryptKeyHasher(KeyHasher):
    """BCrypt hasher.  Non-deterministic (salted), so it cannot be used for
    direct hash-based DB lookup.  Suitable when you store the raw key hint
    separately and verify on retrieval."""

    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    def hash(self, raw_key: str) -> str:
        return bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt(self._rounds)).decode()

    def verify(self, raw_key: str, hashed: str) -> bool:
        return bcrypt.checkpw(raw_key.encode(), hashed.encode())

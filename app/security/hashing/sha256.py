import hashlib
import hmac

from app.security.hashing.base import KeyHasher


class SHA256KeyHasher(KeyHasher):
    """HMAC-SHA256 hasher.  Deterministic: hash(raw) always produces the same
    digest, enabling direct DB lookup by hash."""

    def __init__(self, secret: str = "") -> None:
        self._secret = secret.encode()

    def hash(self, raw_key: str) -> str:
        return hmac.new(self._secret, raw_key.encode(), hashlib.sha256).hexdigest()

    def verify(self, raw_key: str, hashed: str) -> bool:
        return hmac.compare_digest(self.hash(raw_key), hashed)

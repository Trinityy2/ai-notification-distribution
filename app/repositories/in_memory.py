from copy import deepcopy

from app.models.api_key import APIKey
from app.models.result import NotificationLog
from app.repositories.base import APIKeyRepository, NotificationLogRepository


class InMemoryAPIKeyRepository(APIKeyRepository):
    def __init__(self) -> None:
        self._keys: dict[str, APIKey] = {}
        self._hashes: dict[str, str] = {}  # key_id → hash

    async def get_by_id(self, key_id: str) -> APIKey | None:
        return deepcopy(self._keys.get(key_id))

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        for key_id, stored_hash in self._hashes.items():
            if stored_hash == key_hash:
                return deepcopy(self._keys.get(key_id))
        return None

    async def list_all(self) -> list[APIKey]:
        return [deepcopy(k) for k in self._keys.values()]

    async def create(self, key: APIKey, key_hash: str) -> APIKey:
        self._keys[key.id] = deepcopy(key)
        self._hashes[key.id] = key_hash
        return deepcopy(key)

    async def update(self, key_id: str, **kwargs) -> APIKey | None:
        if key_id not in self._keys:
            return None
        key = self._keys[key_id]
        updated = key.model_copy(update=kwargs)
        self._keys[key_id] = updated
        return deepcopy(updated)

    async def delete(self, key_id: str) -> bool:
        if key_id not in self._keys:
            return False
        del self._keys[key_id]
        self._hashes.pop(key_id, None)
        return True


class InMemoryNotificationLogRepository(NotificationLogRepository):
    def __init__(self) -> None:
        self._logs: list[NotificationLog] = []

    async def append(self, entry: NotificationLog) -> None:
        self._logs.append(deepcopy(entry))

    async def list_all(self) -> list[NotificationLog]:
        return [deepcopy(e) for e in self._logs]

    async def list_by_key(self, api_key_id: str) -> list[NotificationLog]:
        return [deepcopy(e) for e in self._logs if e.api_key_id == api_key_id]

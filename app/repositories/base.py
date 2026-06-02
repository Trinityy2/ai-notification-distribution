from abc import ABC, abstractmethod

from app.models.api_key import APIKey
from app.models.result import NotificationLog


class APIKeyRepository(ABC):
    @abstractmethod
    async def get_by_id(self, key_id: str) -> APIKey | None: ...

    @abstractmethod
    async def get_by_hash(self, key_hash: str) -> APIKey | None: ...

    @abstractmethod
    async def list_all(self) -> list[APIKey]: ...

    @abstractmethod
    async def create(self, key: APIKey, key_hash: str) -> APIKey: ...

    @abstractmethod
    async def update(self, key_id: str, **kwargs) -> APIKey | None: ...

    @abstractmethod
    async def delete(self, key_id: str) -> bool: ...


class NotificationLogRepository(ABC):
    @abstractmethod
    async def append(self, entry: NotificationLog) -> None: ...

    @abstractmethod
    async def list_all(self) -> list[NotificationLog]: ...

    @abstractmethod
    async def list_by_key(self, api_key_id: str) -> list[NotificationLog]: ...

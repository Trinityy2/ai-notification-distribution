import pytest
from datetime import datetime, timezone

from app.repositories.in_memory import (
    InMemoryAPIKeyRepository,
    InMemoryNotificationLogRepository,
)
from app.models.api_key import APIKey
from app.models.result import NotificationLog


def _make_key(id: str = "k1", scopes: list[str] | None = None) -> APIKey:
    return APIKey(
        id=id,
        name=f"key-{id}",
        scopes=scopes or ["notify:send"],
        created_at=datetime.now(timezone.utc),
    )


def _make_log(key_id: str = "k1") -> NotificationLog:
    return NotificationLog(
        id="log1",
        api_key_id=key_id,
        target_provider="telegram",
        target_identifier="123",
        status="success",
        timestamp=datetime.now(timezone.utc),
    )


class TestInMemoryAPIKeyRepository:
    @pytest.fixture
    def repo(self) -> InMemoryAPIKeyRepository:
        return InMemoryAPIKeyRepository()

    async def test_create_and_get_by_id(self, repo):
        key = _make_key()
        await repo.create(key, "hash123")
        result = await repo.get_by_id("k1")
        assert result is not None
        assert result.id == "k1"

    async def test_get_by_id_missing_returns_none(self, repo):
        assert await repo.get_by_id("nope") is None

    async def test_get_by_hash(self, repo):
        key = _make_key()
        await repo.create(key, "hash-abc")
        result = await repo.get_by_hash("hash-abc")
        assert result is not None
        assert result.id == "k1"

    async def test_get_by_hash_wrong_hash_returns_none(self, repo):
        key = _make_key()
        await repo.create(key, "hash-abc")
        assert await repo.get_by_hash("wrong-hash") is None

    async def test_list_all(self, repo):
        await repo.create(_make_key("k1"), "h1")
        await repo.create(_make_key("k2"), "h2")
        keys = await repo.list_all()
        assert len(keys) == 2
        ids = {k.id for k in keys}
        assert ids == {"k1", "k2"}

    async def test_update_name(self, repo):
        await repo.create(_make_key(), "h1")
        updated = await repo.update("k1", name="new-name")
        assert updated is not None
        assert updated.name == "new-name"
        # Persisted
        stored = await repo.get_by_id("k1")
        assert stored.name == "new-name"

    async def test_update_missing_returns_none(self, repo):
        result = await repo.update("ghost", name="x")
        assert result is None

    async def test_delete_existing(self, repo):
        await repo.create(_make_key(), "h1")
        assert await repo.delete("k1") is True
        assert await repo.get_by_id("k1") is None

    async def test_delete_missing_returns_false(self, repo):
        assert await repo.delete("ghost") is False

    async def test_returned_objects_are_copies(self, repo):
        """Mutations on returned objects must not affect stored state."""
        key = _make_key()
        await repo.create(key, "h1")
        fetched = await repo.get_by_id("k1")
        fetched.name = "mutated"
        stored = await repo.get_by_id("k1")
        assert stored.name != "mutated"


class TestInMemoryNotificationLogRepository:
    @pytest.fixture
    def repo(self) -> InMemoryNotificationLogRepository:
        return InMemoryNotificationLogRepository()

    async def test_append_and_list_all(self, repo):
        await repo.append(_make_log("k1"))
        await repo.append(_make_log("k2"))
        logs = await repo.list_all()
        assert len(logs) == 2

    async def test_list_by_key_filters(self, repo):
        await repo.append(_make_log("k1"))
        await repo.append(_make_log("k1"))
        await repo.append(_make_log("k2"))
        logs = await repo.list_by_key("k1")
        assert len(logs) == 2
        assert all(l.api_key_id == "k1" for l in logs)

    async def test_list_by_key_empty(self, repo):
        assert await repo.list_by_key("nobody") == []

    async def test_returned_logs_are_copies(self, repo):
        await repo.append(_make_log())
        logs = await repo.list_all()
        logs[0].status = "mutated"
        assert (await repo.list_all())[0].status != "mutated"

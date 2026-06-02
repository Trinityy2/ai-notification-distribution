import pytest
from tests.conftest import ADMIN_RAW_KEY, READONLY_RAW_KEY, NOTIFY_RAW_KEY


class TestListKeys:
    async def test_admin_can_list(self, app_client):
        resp = await app_client.get("/keys", headers={"X-API-Key": ADMIN_RAW_KEY})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_readonly_can_list(self, app_client):
        resp = await app_client.get("/keys", headers={"X-API-Key": READONLY_RAW_KEY})
        assert resp.status_code == 200

    async def test_notify_only_key_cannot_list(self, app_client):
        resp = await app_client.get("/keys", headers={"X-API-Key": NOTIFY_RAW_KEY})
        assert resp.status_code == 403


class TestCreateKey:
    async def test_admin_can_create(self, app_client):
        resp = await app_client.post(
            "/keys",
            headers={"X-API-Key": ADMIN_RAW_KEY},
            json={"name": "new-key", "scopes": ["notify:send"]},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "new-key"
        assert "raw_key" in body
        assert len(body["raw_key"]) > 10  # non-trivial secret

    async def test_raw_key_not_in_subsequent_get(self, app_client):
        create_resp = await app_client.post(
            "/keys",
            headers={"X-API-Key": ADMIN_RAW_KEY},
            json={"name": "ephemeral", "scopes": ["notify:send"]},
        )
        key_id = create_resp.json()["id"]
        get_resp = await app_client.get(f"/keys/{key_id}", headers={"X-API-Key": ADMIN_RAW_KEY})
        assert "raw_key" not in get_resp.json()

    async def test_readonly_cannot_create(self, app_client):
        resp = await app_client.post(
            "/keys",
            headers={"X-API-Key": READONLY_RAW_KEY},
            json={"name": "x", "scopes": ["notify:send"]},
        )
        assert resp.status_code == 403

    async def test_keys_write_implies_keys_read(self, app_client, key_repo, log_repo, mock_provider):
        """A key with only keys:write should still pass GET /keys (keys:read implied)."""
        from app.config import Settings
        from app.container import Container
        from app.providers.registry import ProviderRegistry
        from app.security.hashing.sha256 import SHA256KeyHasher
        from app.security.rate_limiting.in_memory import InMemoryRateLimiter
        from app.main import create_app
        from app.models.api_key import APIKey
        from httpx import ASGITransport, AsyncClient
        from datetime import datetime, timezone

        write_raw = "write-only-raw-key"
        hasher = SHA256KeyHasher(secret="test-secret")
        write_key = APIKey(id="write-only", name="write-only", scopes=["keys:write"], created_at=datetime.now(timezone.utc))
        await key_repo.create(write_key, hasher.hash(write_raw))

        settings = Settings(environment="development", repository_backend="in_memory", hasher_secret="test-secret")
        registry = ProviderRegistry()
        registry.register("mock", mock_provider)

        container = Container(settings)
        container._key_repo = key_repo
        container._log_repo = log_repo
        container._hasher = hasher
        container._rate_limiter = InMemoryRateLimiter()
        container._provider_registry = registry

        fastapi_app = create_app()
        fastapi_app.state.container = container

        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
            resp = await client.get("/keys", headers={"X-API-Key": write_raw})
        assert resp.status_code == 200


class TestGetKey:
    async def test_get_existing_key(self, app_client):
        resp = await app_client.get("/keys/notify-key", headers={"X-API-Key": ADMIN_RAW_KEY})
        assert resp.status_code == 200
        assert resp.json()["id"] == "notify-key"

    async def test_get_missing_key_returns_404(self, app_client):
        resp = await app_client.get("/keys/ghost", headers={"X-API-Key": ADMIN_RAW_KEY})
        assert resp.status_code == 404


class TestUpdateKey:
    async def test_admin_can_update_name(self, app_client):
        resp = await app_client.patch(
            "/keys/notify-key",
            headers={"X-API-Key": ADMIN_RAW_KEY},
            json={"name": "renamed"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "renamed"

    async def test_admin_can_deactivate_key(self, app_client):
        resp = await app_client.patch(
            "/keys/notify-key",
            headers={"X-API-Key": ADMIN_RAW_KEY},
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_empty_update_returns_422(self, app_client):
        resp = await app_client.patch(
            "/keys/notify-key",
            headers={"X-API-Key": ADMIN_RAW_KEY},
            json={},
        )
        assert resp.status_code == 422

    async def test_update_missing_key_returns_404(self, app_client):
        resp = await app_client.patch(
            "/keys/ghost",
            headers={"X-API-Key": ADMIN_RAW_KEY},
            json={"name": "x"},
        )
        assert resp.status_code == 404

    async def test_readonly_cannot_update(self, app_client):
        resp = await app_client.patch(
            "/keys/notify-key",
            headers={"X-API-Key": READONLY_RAW_KEY},
            json={"name": "x"},
        )
        assert resp.status_code == 403


class TestDeleteKey:
    async def test_admin_can_delete(self, app_client):
        resp = await app_client.delete("/keys/notify-key", headers={"X-API-Key": ADMIN_RAW_KEY})
        assert resp.status_code == 204

    async def test_delete_missing_returns_404(self, app_client):
        resp = await app_client.delete("/keys/ghost", headers={"X-API-Key": ADMIN_RAW_KEY})
        assert resp.status_code == 404

    async def test_readonly_cannot_delete(self, app_client):
        resp = await app_client.delete("/keys/notify-key", headers={"X-API-Key": READONLY_RAW_KEY})
        assert resp.status_code == 403

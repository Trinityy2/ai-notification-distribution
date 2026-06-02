import pytest
from tests.conftest import NOTIFY_RAW_KEY, ADMIN_RAW_KEY, READONLY_RAW_KEY


class TestMissingKey:
    async def test_no_header_returns_401(self, app_client):
        resp = await app_client.get("/keys")
        assert resp.status_code == 401

    async def test_empty_header_returns_401(self, app_client):
        resp = await app_client.get("/keys", headers={"X-API-Key": ""})
        assert resp.status_code == 401


class TestInvalidKey:
    async def test_wrong_key_returns_401(self, app_client):
        resp = await app_client.get("/keys", headers={"X-API-Key": "totally-wrong"})
        assert resp.status_code == 401

    async def test_wrong_key_error_message(self, app_client):
        resp = await app_client.get("/keys", headers={"X-API-Key": "bad"})
        assert "Invalid API key" in resp.json()["detail"]


class TestInactiveKey:
    async def test_inactive_key_returns_401(self, app_client, key_repo):
        await key_repo.update("notify-key", is_active=False)
        resp = await app_client.post(
            "/notify",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={"target": {"provider": "mock", "identifier": "abc"}, "message": {"text": "hi"}},
        )
        assert resp.status_code == 401

    async def test_inactive_key_detail(self, app_client, key_repo):
        await key_repo.update("notify-key", is_active=False)
        resp = await app_client.post(
            "/notify",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={"target": {"provider": "mock", "identifier": "abc"}, "message": {"text": "hi"}},
        )
        assert "inactive" in resp.json()["detail"].lower()


class TestValidKey:
    async def test_valid_key_passes_auth(self, app_client):
        resp = await app_client.get("/health")
        assert resp.status_code == 200  # health is unauthenticated

    async def test_notify_key_can_send(self, app_client):
        resp = await app_client.post(
            "/notify",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={"target": {"provider": "mock", "identifier": "abc"}, "message": {"text": "hi"}},
        )
        assert resp.status_code == 200

    async def test_admin_key_can_access_keys(self, app_client):
        resp = await app_client.get("/keys", headers={"X-API-Key": ADMIN_RAW_KEY})
        assert resp.status_code == 200


class TestRateLimiting:
    async def test_rate_limit_exceeded_returns_429(self, key_repo, log_repo, mock_provider):
        """Configure a very low limit and hammer the endpoint."""
        from app.config import Settings
        from app.container import Container
        from app.providers.registry import ProviderRegistry
        from app.security.hashing.sha256 import SHA256KeyHasher
        from app.security.rate_limiting.in_memory import InMemoryRateLimiter
        from app.main import create_app
        from app.dependencies import get_container
        from httpx import ASGITransport, AsyncClient

        settings = Settings(
            environment="development",
            repository_backend="in_memory",
            hasher_secret="test-secret",
        )
        registry = ProviderRegistry()
        registry.register("mock", mock_provider)

        container = Container(settings)
        container._key_repo = key_repo
        container._log_repo = log_repo
        container._hasher = SHA256KeyHasher(secret="test-secret")
        container._rate_limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
        container._provider_registry = registry

        fastapi_app = create_app(settings)
        fastapi_app.dependency_overrides[get_container] = lambda: container

        async with AsyncClient(
            transport=ASGITransport(app=fastapi_app), base_url="http://test"
        ) as client:
            for _ in range(2):
                await client.post(
                    "/notify",
                    headers={"X-API-Key": NOTIFY_RAW_KEY},
                    json={"target": {"provider": "mock", "identifier": "x"}, "message": {"text": "y"}},
                )
            resp = await client.post(
                "/notify",
                headers={"X-API-Key": NOTIFY_RAW_KEY},
                json={"target": {"provider": "mock", "identifier": "x"}, "message": {"text": "y"}},
            )
        assert resp.status_code == 429

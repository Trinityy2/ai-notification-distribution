"""Integration tests for middleware and app-level behaviour."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.container import Container
from app.main import create_app
from app.providers.registry import ProviderRegistry
from app.repositories.in_memory import InMemoryAPIKeyRepository, InMemoryNotificationLogRepository
from app.security.hashing.sha256 import SHA256KeyHasher
from app.security.rate_limiting.in_memory import InMemoryRateLimiter
from tests.conftest import MockMessagingProvider, NOTIFY_RAW_KEY, ADMIN_RAW_KEY, HASHER, _make_key
from datetime import datetime, timezone


async def _build_client(settings, key_repo, log_repo, mock_provider):
    registry = ProviderRegistry()
    registry.register("mock", mock_provider)
    container = Container(settings)
    container._key_repo = key_repo
    container._log_repo = log_repo
    container._hasher = HASHER
    container._rate_limiter = InMemoryRateLimiter()
    container._provider_registry = registry
    fastapi_app = create_app(settings)
    from app.dependencies import get_container
    fastapi_app.dependency_overrides[get_container] = lambda: container
    return fastapi_app


class TestBodySizeLimit:
    async def test_large_body_returns_413(self, key_repo, log_repo, mock_provider):
        fastapi_app = await _build_client(
            Settings(environment="development", repository_backend="in_memory", hasher_secret="test-secret"),
            key_repo, log_repo, mock_provider,
        )
        huge_text = "x" * (64 * 1024 + 1)
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
            resp = await client.post(
                "/notify",
                headers={"X-API-Key": NOTIFY_RAW_KEY, "Content-Length": str(len(huge_text) + 200)},
                json={"target": {"provider": "mock", "identifier": "a"}, "message": {"text": huge_text}},
            )
        assert resp.status_code == 413


class TestProductionApp:
    async def test_openapi_not_accessible_in_production(self, key_repo, log_repo, mock_provider):
        """In production, openapi.json is either 307 (HTTPS redirect) or 404 (route disabled)."""
        fastapi_app = await _build_client(
            Settings(environment="production", repository_backend="in_memory", hasher_secret="test-secret"),
            key_repo, log_repo, mock_provider,
        )
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
            resp = await client.get("/openapi.json", follow_redirects=False)
        assert resp.status_code not in (200,)

    async def test_docs_not_accessible_in_production(self, key_repo, log_repo, mock_provider):
        fastapi_app = await _build_client(
            Settings(environment="production", repository_backend="in_memory", hasher_secret="test-secret"),
            key_repo, log_repo, mock_provider,
        )
        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
            resp = await client.get("/docs", follow_redirects=False)
        assert resp.status_code not in (200,)

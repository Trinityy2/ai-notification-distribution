"""Shared test fixtures.

All tests use InMemory repositories and a MockMessagingProvider so:
- No real DB required
- No real HTTP calls to messaging platforms
- Tests are fast and isolated
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.container import Container
from app.config import Settings
from app.main import create_app
from app.models.api_key import APIKey
from app.models.message import Message
from app.models.result import SendResult
from app.models.target import Target
from app.providers.base import MessagingProvider
from app.providers.registry import ProviderRegistry
from app.repositories.in_memory import (
    InMemoryAPIKeyRepository,
    InMemoryNotificationLogRepository,
)
from app.security.hashing.sha256 import SHA256KeyHasher
from app.security.rate_limiting.in_memory import InMemoryRateLimiter
from datetime import datetime, timezone


# ── Mock provider ─────────────────────────────────────────────────────────────

class MockMessagingProvider(MessagingProvider):
    """Records calls without making real HTTP requests."""

    def __init__(self, should_fail: bool = False) -> None:
        self.calls: list[tuple[Target, Message]] = []
        self.should_fail = should_fail

    async def send(self, target: Target, message: Message) -> SendResult:
        self.calls.append((target, message))
        if self.should_fail:
            return SendResult(
                success=False,
                provider=target.provider,
                identifier=target.identifier,
                error="Mock failure",
            )
        return SendResult(success=True, provider=target.provider, identifier=target.identifier)

    async def validate_target(self, target: Target) -> None:
        pass  # accept everything


# ── Hasher & raw keys ─────────────────────────────────────────────────────────

HASHER = SHA256KeyHasher(secret="test-secret")

NOTIFY_RAW_KEY = "notify-key-raw-value"
ADMIN_RAW_KEY = "admin-key-raw-value"
READONLY_RAW_KEY = "readonly-key-raw-value"


def _make_key(key_id: str, scopes: list[str]) -> APIKey:
    return APIKey(id=key_id, name=key_id, scopes=scopes, created_at=datetime.now(timezone.utc))


# ── App + client fixture ──────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def mock_provider():
    return MockMessagingProvider()


@pytest_asyncio.fixture
async def failing_provider():
    return MockMessagingProvider(should_fail=True)


@pytest_asyncio.fixture
async def key_repo():
    repo = InMemoryAPIKeyRepository()
    await repo.create(_make_key("notify-key", ["notify:send"]), HASHER.hash(NOTIFY_RAW_KEY))
    await repo.create(_make_key("admin-key", ["admin"]), HASHER.hash(ADMIN_RAW_KEY))
    await repo.create(_make_key("readonly-key", ["keys:read"]), HASHER.hash(READONLY_RAW_KEY))
    return repo


@pytest_asyncio.fixture
async def log_repo():
    return InMemoryNotificationLogRepository()


@pytest_asyncio.fixture
async def app_client(key_repo, log_repo, mock_provider):
    """Full test app with InMemory deps and mock provider injected."""
    settings = Settings(
        environment="development",
        repository_backend="in_memory",
        hasher_backend="sha256",
        hasher_secret="test-secret",
    )

    registry = ProviderRegistry()
    registry.register("mock", mock_provider)

    container = Container(settings)
    container._key_repo = key_repo
    container._log_repo = log_repo
    container._hasher = HASHER
    container._rate_limiter = InMemoryRateLimiter(max_requests=100, window_seconds=60)
    container._provider_registry = registry

    fastapi_app = create_app(settings)
    # Override get_container so all dependencies use our test container
    from app.dependencies import get_container
    fastapi_app.dependency_overrides[get_container] = lambda: container

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as client:
        yield client


@pytest_asyncio.fixture
async def app_client_failing(key_repo, log_repo, failing_provider):
    """App with a provider that always returns failure."""
    settings = Settings(
        environment="development",
        repository_backend="in_memory",
        hasher_backend="sha256",
        hasher_secret="test-secret",
    )

    registry = ProviderRegistry()
    registry.register("mock", failing_provider)

    container = Container(settings)
    container._key_repo = key_repo
    container._log_repo = log_repo
    container._hasher = HASHER
    container._rate_limiter = InMemoryRateLimiter(max_requests=100, window_seconds=60)
    container._provider_registry = registry

    fastapi_app = create_app(settings)
    from app.dependencies import get_container
    fastapi_app.dependency_overrides[get_container] = lambda: container

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as client:
        yield client

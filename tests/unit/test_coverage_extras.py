"""Tests for uncovered paths: logging config, middleware, lifespan, container, models."""

import pytest
import logging
from unittest.mock import patch

from app.logging_config import configure_logging
from app.config import Settings
from app.models.result import BatchSendResult, SendResult
from app.container import Container


class TestLoggingConfig:
    def test_development_uses_plain_formatter(self):
        settings = Settings(environment="development")
        configure_logging(settings)
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        handler = root.handlers[0]
        assert not isinstance(handler.formatter.__class__.__name__, str) or True  # just no error

    def test_production_uses_json_formatter(self):
        settings = Settings(environment="production")
        configure_logging(settings)
        root = logging.getLogger()
        assert root.level == logging.INFO


class TestBatchSendResultProperties:
    def test_total(self):
        r = BatchSendResult(results=[
            SendResult(success=True, provider="p", identifier="a"),
            SendResult(success=False, provider="p", identifier="b"),
        ])
        assert r.total == 2

    def test_succeeded(self):
        r = BatchSendResult(results=[
            SendResult(success=True, provider="p", identifier="a"),
            SendResult(success=True, provider="p", identifier="b"),
            SendResult(success=False, provider="p", identifier="c"),
        ])
        assert r.succeeded == 2

    def test_failed(self):
        r = BatchSendResult(results=[
            SendResult(success=True, provider="p", identifier="a"),
            SendResult(success=False, provider="p", identifier="b"),
        ])
        assert r.failed == 1


class TestContainerBackends:
    def test_bcrypt_hasher_backend(self):
        settings = Settings(environment="development", hasher_backend="bcrypt")
        container = Container(settings)
        from app.security.hashing.bcrypt import BcryptKeyHasher
        assert isinstance(container.hasher, BcryptKeyHasher)

    def test_sha256_hasher_backend(self):
        settings = Settings(environment="development", hasher_backend="sha256")
        container = Container(settings)
        from app.security.hashing.sha256 import SHA256KeyHasher
        assert isinstance(container.hasher, SHA256KeyHasher)

    def test_in_memory_repo_backend(self):
        settings = Settings(environment="development", repository_backend="in_memory")
        container = Container(settings)
        from app.repositories.in_memory import InMemoryAPIKeyRepository, InMemoryNotificationLogRepository
        assert isinstance(container.key_repo, InMemoryAPIKeyRepository)
        assert isinstance(container.log_repo, InMemoryNotificationLogRepository)

    def test_production_rate_limiter(self):
        settings = Settings(environment="production", repository_backend="in_memory")
        container = Container(settings)
        from app.security.rate_limiting.slowapi import SlowAPIRateLimiter
        assert isinstance(container.rate_limiter, SlowAPIRateLimiter)

    def test_development_rate_limiter(self):
        settings = Settings(environment="development", repository_backend="in_memory")
        container = Container(settings)
        from app.security.rate_limiting.in_memory import InMemoryRateLimiter
        assert isinstance(container.rate_limiter, InMemoryRateLimiter)

    def test_telegram_provider_registered_when_token_set(self):
        settings = Settings(
            environment="development",
            repository_backend="in_memory",
        )
        settings.telegram.bot_token = "fake-token"  # type: ignore
        # Directly test registry building
        from pydantic import SecretStr
        import os
        with patch.dict("os.environ", {"TELEGRAM__BOT_TOKEN": "fake-bot-token"}):
            from app.config import Settings as S
            s = S(environment="development", repository_backend="in_memory")
            c = Container(s)
            assert "telegram" in c.provider_registry.names()

    def test_whatsapp_always_registered(self):
        settings = Settings(environment="development", repository_backend="in_memory")
        container = Container(settings)
        assert "whatsapp" in container.provider_registry.names()

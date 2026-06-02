"""Dependency-injection container.

Wires abstract interfaces to concrete implementations based on Settings.
Swap any backend by changing an env var — no application code changes required.
"""

import logging

from app.config import Settings
from app.providers.registry import ProviderRegistry
from app.providers.telegram import TelegramProvider
from app.providers.whatsapp import WhatsAppProvider
from app.repositories.base import APIKeyRepository, NotificationLogRepository
from app.repositories.in_memory import (
    InMemoryAPIKeyRepository,
    InMemoryNotificationLogRepository,
)
from app.security.hashing.base import KeyHasher
from app.security.hashing.bcrypt import BcryptKeyHasher
from app.security.hashing.sha256 import SHA256KeyHasher
from app.security.rate_limiting.base import RateLimiter
from app.security.rate_limiting.in_memory import InMemoryRateLimiter
from app.security.rate_limiting.slowapi import SlowAPIRateLimiter

logger = logging.getLogger(__name__)


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._key_repo: APIKeyRepository | None = None
        self._log_repo: NotificationLogRepository | None = None
        self._hasher: KeyHasher | None = None
        self._rate_limiter: RateLimiter | None = None
        self._provider_registry: ProviderRegistry | None = None

    # ── Repositories ───────────────────────────────────────────────────────────

    @property
    def key_repo(self) -> APIKeyRepository:
        if self._key_repo is None:
            self._key_repo = self._build_key_repo()
        return self._key_repo

    @property
    def log_repo(self) -> NotificationLogRepository:
        if self._log_repo is None:
            self._log_repo = self._build_log_repo()
        return self._log_repo

    def _build_key_repo(self) -> APIKeyRepository:
        if self.settings.repository_backend == "sqlalchemy":
            from app.repositories.sqlalchemy.api_key_repository import (
                SQLAlchemyAPIKeyRepository,
            )
            from app.repositories.sqlalchemy.session import get_session_factory

            session_factory = get_session_factory(
                self.settings.database_url.get_secret_value()
            )
            logger.info("Using SQLAlchemyAPIKeyRepository")
            return SQLAlchemyAPIKeyRepository(session_factory)
        logger.info("Using InMemoryAPIKeyRepository")
        return InMemoryAPIKeyRepository()

    def _build_log_repo(self) -> NotificationLogRepository:
        if self.settings.repository_backend == "sqlalchemy":
            from app.repositories.sqlalchemy.log_repository import (
                SQLAlchemyNotificationLogRepository,
            )
            from app.repositories.sqlalchemy.session import get_session_factory

            session_factory = get_session_factory(
                self.settings.database_url.get_secret_value()
            )
            logger.info("Using SQLAlchemyNotificationLogRepository")
            return SQLAlchemyNotificationLogRepository(session_factory)
        logger.info("Using InMemoryNotificationLogRepository")
        return InMemoryNotificationLogRepository()

    # ── Security ───────────────────────────────────────────────────────────────

    @property
    def hasher(self) -> KeyHasher:
        if self._hasher is None:
            self._hasher = self._build_hasher()
        return self._hasher

    def _build_hasher(self) -> KeyHasher:
        if self.settings.hasher_backend == "bcrypt":
            logger.info("Using BcryptKeyHasher")
            return BcryptKeyHasher()
        logger.info("Using SHA256KeyHasher")
        return SHA256KeyHasher(secret=self.settings.hasher_secret)

    @property
    def rate_limiter(self) -> RateLimiter:
        if self._rate_limiter is None:
            self._rate_limiter = self._build_rate_limiter()
        return self._rate_limiter

    def _build_rate_limiter(self) -> RateLimiter:
        if self.settings.environment == "production":
            logger.info("Using SlowAPIRateLimiter")
            return SlowAPIRateLimiter(
                max_requests=self.settings.rate_limit_requests,
                window_seconds=self.settings.rate_limit_window_seconds,
            )
        logger.info("Using InMemoryRateLimiter")
        return InMemoryRateLimiter(
            max_requests=self.settings.rate_limit_requests,
            window_seconds=self.settings.rate_limit_window_seconds,
        )

    # ── Providers ──────────────────────────────────────────────────────────────

    @property
    def provider_registry(self) -> ProviderRegistry:
        if self._provider_registry is None:
            self._provider_registry = self._build_provider_registry()
        return self._provider_registry

    def _build_provider_registry(self) -> ProviderRegistry:
        registry = ProviderRegistry()

        tg_token = self.settings.telegram.bot_token
        if tg_token:
            registry.register("telegram", TelegramProvider(tg_token.get_secret_value()))
            logger.info("Registered provider: telegram")
        else:
            logger.warning("TELEGRAM__BOT_TOKEN not set — telegram provider disabled")

        registry.register("whatsapp", WhatsAppProvider())
        logger.info("Registered provider: whatsapp (stub)")

        return registry

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramSettings(BaseSettings):
    bot_token: SecretStr | None = None

    model_config = SettingsConfigDict(env_prefix="TELEGRAM__", env_file=(".env", ".env.local"), extra="ignore")


class Settings(BaseSettings):
    environment: Literal["development", "production"] = "development"
    admin_root_key: SecretStr | None = None

    repository_backend: Literal["sqlalchemy", "in_memory"] = "sqlalchemy"
    database_url: SecretStr | None = None

    hasher_backend: Literal["sha256", "bcrypt"] = "sha256"
    hasher_secret: str = ""

    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    # File logging (optional — stdout only when log_file is unset)
    log_file: str | None = None
    log_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    log_backup_count: int = 5

    telegram: TelegramSettings = TelegramSettings()

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_nested_delimiter="__",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

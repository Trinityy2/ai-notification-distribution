from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class APIKeyORM(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    scopes: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded list
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class NotificationLogORM(Base):
    __tablename__ = "notification_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    api_key_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    target_identifier: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

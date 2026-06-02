from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.result import NotificationLog
from app.repositories.base import NotificationLogRepository
from app.repositories.sqlalchemy.models import NotificationLogORM


def _orm_to_domain(orm: NotificationLogORM) -> NotificationLog:
    return NotificationLog(
        id=orm.id,
        api_key_id=orm.api_key_id,
        target_provider=orm.target_provider,
        target_identifier=orm.target_identifier,
        status=orm.status,
        error=orm.error,
        timestamp=orm.timestamp,
    )


class SQLAlchemyNotificationLogRepository(NotificationLogRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def append(self, entry: NotificationLog) -> None:
        async with self._factory() as session:
            orm = NotificationLogORM(
                id=entry.id,
                api_key_id=entry.api_key_id,
                target_provider=entry.target_provider,
                target_identifier=entry.target_identifier,
                status=entry.status,
                error=entry.error,
                timestamp=entry.timestamp,
            )
            session.add(orm)
            await session.commit()

    async def list_all(self) -> list[NotificationLog]:
        async with self._factory() as session:
            result = await session.execute(select(NotificationLogORM))
            return [_orm_to_domain(row) for row in result.scalars()]

    async def list_by_key(self, api_key_id: str) -> list[NotificationLog]:
        async with self._factory() as session:
            result = await session.execute(
                select(NotificationLogORM).where(
                    NotificationLogORM.api_key_id == api_key_id
                )
            )
            return [_orm_to_domain(row) for row in result.scalars()]

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.api_key import APIKey
from app.repositories.base import APIKeyRepository
from app.repositories.sqlalchemy.models import APIKeyORM


def _orm_to_domain(orm: APIKeyORM) -> APIKey:
    return APIKey(
        id=orm.id,
        name=orm.name,
        scopes=json.loads(orm.scopes),
        is_active=orm.is_active,
        created_at=orm.created_at,
    )


class SQLAlchemyAPIKeyRepository(APIKeyRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._factory = session_factory

    async def get_by_id(self, key_id: str) -> APIKey | None:
        async with self._factory() as session:
            orm = await session.get(APIKeyORM, key_id)
            return _orm_to_domain(orm) if orm else None

    async def get_by_hash(self, key_hash: str) -> APIKey | None:
        async with self._factory() as session:
            result = await session.execute(
                select(APIKeyORM).where(APIKeyORM.key_hash == key_hash)
            )
            orm = result.scalar_one_or_none()
            return _orm_to_domain(orm) if orm else None

    async def list_all(self) -> list[APIKey]:
        async with self._factory() as session:
            result = await session.execute(select(APIKeyORM))
            return [_orm_to_domain(row) for row in result.scalars()]

    async def create(self, key: APIKey, key_hash: str) -> APIKey:
        async with self._factory() as session:
            orm = APIKeyORM(
                id=key.id,
                name=key.name,
                key_hash=key_hash,
                scopes=json.dumps(key.scopes),
                is_active=key.is_active,
                created_at=key.created_at,
            )
            session.add(orm)
            await session.commit()
            return key

    async def update(self, key_id: str, **kwargs) -> APIKey | None:
        async with self._factory() as session:
            orm = await session.get(APIKeyORM, key_id)
            if orm is None:
                return None
            if "name" in kwargs:
                orm.name = kwargs["name"]
            if "scopes" in kwargs:
                orm.scopes = json.dumps(kwargs["scopes"])
            if "is_active" in kwargs:
                orm.is_active = kwargs["is_active"]
            await session.commit()
            await session.refresh(orm)
            return _orm_to_domain(orm)

    async def delete(self, key_id: str) -> bool:
        async with self._factory() as session:
            orm = await session.get(APIKeyORM, key_id)
            if orm is None:
                return False
            await session.delete(orm)
            await session.commit()
            return True

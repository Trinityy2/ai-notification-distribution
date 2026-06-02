"""FastAPI shared dependencies.

The Container is stored on app.state at startup so all dependencies can reach
it without importing a global singleton.
"""

import logging

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from app.models.api_key import APIKey

logger = logging.getLogger(__name__)

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_container(request: Request):
    return request.app.state.container


def get_key_repo(container=Depends(get_container)):
    return container.key_repo


def get_log_repo(container=Depends(get_container)):
    return container.log_repo


def get_hasher(container=Depends(get_container)):
    return container.hasher


def get_rate_limiter(container=Depends(get_container)):
    return container.rate_limiter


def get_provider_registry(container=Depends(get_container)):
    return container.provider_registry


async def get_current_key(
    raw_key: str | None = Security(_API_KEY_HEADER),
    key_repo=Depends(get_key_repo),
    hasher=Depends(get_hasher),
    rate_limiter=Depends(get_rate_limiter),
) -> APIKey:
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide it in the X-API-Key header.",
        )

    key_hash = hasher.hash(raw_key)
    key = await key_repo.get_by_hash(key_hash)

    if key is None:
        logger.warning("Auth failed: unknown API key (hash not found)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    if not key.is_active:
        logger.warning("Auth failed: inactive API key", extra={"key_id": key.id})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is inactive.",
        )

    from app.security.rate_limiting.base import RateLimitExceeded

    try:
        await rate_limiter.check(key.id)
    except RateLimitExceeded:
        logger.warning("Rate limit exceeded", extra={"key_id": key.id})
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down.",
        )

    return key

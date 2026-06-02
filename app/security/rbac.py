from enum import Enum
from typing import Callable

from fastapi import Depends, HTTPException, status

from app.models.api_key import APIKey


class Scope(str, Enum):
    NOTIFY_SEND = "notify:send"
    KEYS_READ = "keys:read"
    KEYS_WRITE = "keys:write"
    ADMIN = "admin"


# Implication rules: granting a scope also grants all implied scopes.
SCOPE_IMPLICATIONS: dict[Scope, set[Scope]] = {
    Scope.KEYS_WRITE: {Scope.KEYS_READ},
    Scope.ADMIN: {Scope.NOTIFY_SEND, Scope.KEYS_READ, Scope.KEYS_WRITE},
}


def expand_scopes(scopes: list[str]) -> set[Scope]:
    """Return the full set of effective scopes after applying implication rules."""
    effective: set[Scope] = set()
    for raw in scopes:
        try:
            scope = Scope(raw)
        except ValueError:
            continue
        effective.add(scope)
        effective.update(SCOPE_IMPLICATIONS.get(scope, set()))
    return effective


def require_scope(required: Scope) -> Callable:
    """FastAPI dependency factory.  Raises 403 if the key lacks *required*.

    ``app.dependencies`` is imported inside the function to avoid circular
    imports (dependencies.py → security → rbac → dependencies).

    Usage::

        @router.post("/notify", dependencies=[Depends(require_scope(Scope.NOTIFY_SEND))])
        async def notify(...): ...
    """
    from app.dependencies import get_current_key

    def _check(current_key: APIKey = Depends(get_current_key)) -> APIKey:
        if not current_key.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key is inactive.",
            )
        effective = expand_scopes(current_key.scopes)
        if required not in effective:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{required.value}' required.",
            )
        return current_key

    return _check


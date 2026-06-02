import pytest

from app.security.rbac import Scope, expand_scopes, require_scope
from app.models.api_key import APIKey
from fastapi import HTTPException
from datetime import datetime, timezone


def _key(scopes: list[str]) -> APIKey:
    return APIKey(id="test", name="test", scopes=scopes, created_at=datetime.now(timezone.utc))


class TestExpandScopes:
    def test_single_scope_no_implication(self):
        result = expand_scopes([Scope.NOTIFY_SEND])
        assert Scope.NOTIFY_SEND in result

    def test_keys_write_implies_keys_read(self):
        result = expand_scopes([Scope.KEYS_WRITE])
        assert Scope.KEYS_READ in result
        assert Scope.KEYS_WRITE in result

    def test_admin_implies_all_scopes(self):
        result = expand_scopes([Scope.ADMIN])
        assert Scope.NOTIFY_SEND in result
        assert Scope.KEYS_READ in result
        assert Scope.KEYS_WRITE in result
        assert Scope.ADMIN in result

    def test_unknown_scope_strings_are_ignored(self):
        """Non-enum scope strings should not raise; they just won't expand."""
        result = expand_scopes(["unknown:scope"])
        assert result == set()

    def test_empty_scopes(self):
        assert expand_scopes([]) == set()


class TestRequireScope:
    """Call the inner _check function directly (bypassing FastAPI DI)."""

    def test_exact_scope_granted(self):
        key = _key([Scope.NOTIFY_SEND])
        check = require_scope(Scope.NOTIFY_SEND)
        check(current_key=key)  # should not raise

    def test_implied_scope_granted(self):
        """keys:write holder should pass a keys:read check."""
        key = _key([Scope.KEYS_WRITE])
        check = require_scope(Scope.KEYS_READ)
        check(current_key=key)

    def test_admin_passes_any_scope(self):
        key = _key([Scope.ADMIN])
        for scope in [Scope.NOTIFY_SEND, Scope.KEYS_READ, Scope.KEYS_WRITE]:
            check = require_scope(scope)
            check(current_key=key)

    def test_missing_scope_raises_403(self):
        key = _key([Scope.NOTIFY_SEND])
        check = require_scope(Scope.KEYS_READ)
        with pytest.raises(HTTPException) as exc_info:
            check(current_key=key)
        assert exc_info.value.status_code == 403

    def test_inactive_key_raises_403(self):
        key = _key([Scope.ADMIN])
        key.is_active = False
        check = require_scope(Scope.NOTIFY_SEND)
        with pytest.raises(HTTPException) as exc_info:
            check(current_key=key)
        assert exc_info.value.status_code == 403

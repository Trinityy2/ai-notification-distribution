import pytest
from tests.conftest import NOTIFY_RAW_KEY, ADMIN_RAW_KEY, READONLY_RAW_KEY


class TestSingleNotify:
    async def test_successful_send(self, app_client, log_repo):
        resp = await app_client.post(
            "/notify",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={"target": {"provider": "mock", "identifier": "abc"}, "message": {"text": "hello"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["provider"] == "mock"
        assert body["identifier"] == "abc"

    async def test_audit_log_written_on_success(self, app_client, log_repo):
        await app_client.post(
            "/notify",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={"target": {"provider": "mock", "identifier": "abc"}, "message": {"text": "hello"}},
        )
        logs = await log_repo.list_all()
        assert len(logs) == 1
        assert logs[0].status == "success"
        assert logs[0].target_provider == "mock"
        assert logs[0].api_key_id == "notify-key"

    async def test_audit_log_written_on_failure(self, app_client_failing, log_repo):
        await app_client_failing.post(
            "/notify",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={"target": {"provider": "mock", "identifier": "abc"}, "message": {"text": "hello"}},
        )
        logs = await log_repo.list_all()
        assert len(logs) == 1
        assert logs[0].status == "failure"

    async def test_unknown_provider_returns_200_with_failure(self, app_client, log_repo):
        resp = await app_client.post(
            "/notify",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={"target": {"provider": "nonexistent", "identifier": "abc"}, "message": {"text": "hi"}},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is False
        logs = await log_repo.list_all()
        assert logs[0].status == "failure"

    async def test_missing_auth_returns_401(self, app_client):
        resp = await app_client.post(
            "/notify",
            json={"target": {"provider": "mock", "identifier": "abc"}, "message": {"text": "hi"}},
        )
        assert resp.status_code == 401

    async def test_wrong_scope_returns_403(self, app_client):
        resp = await app_client.post(
            "/notify",
            headers={"X-API-Key": READONLY_RAW_KEY},
            json={"target": {"provider": "mock", "identifier": "abc"}, "message": {"text": "hi"}},
        )
        assert resp.status_code == 403

    async def test_notify_with_title(self, app_client, mock_provider):
        await app_client.post(
            "/notify",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={"target": {"provider": "mock", "identifier": "abc"}, "message": {"text": "body", "title": "Alert"}},
        )
        assert len(mock_provider.calls) == 1
        _, msg = mock_provider.calls[0]
        assert msg.title == "Alert"


class TestBatchNotify:
    async def test_batch_dispatches_all_targets(self, app_client, mock_provider, log_repo):
        resp = await app_client.post(
            "/notify/batch",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={
                "targets": [
                    {"provider": "mock", "identifier": "t1"},
                    {"provider": "mock", "identifier": "t2"},
                    {"provider": "mock", "identifier": "t3"},
                ],
                "message": {"text": "broadcast"},
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["results"]) == 3
        assert all(r["success"] for r in body["results"])
        assert len(mock_provider.calls) == 3

    async def test_batch_audit_log_per_target(self, app_client, log_repo):
        await app_client.post(
            "/notify/batch",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={
                "targets": [
                    {"provider": "mock", "identifier": "t1"},
                    {"provider": "mock", "identifier": "t2"},
                ],
                "message": {"text": "hi"},
            },
        )
        logs = await log_repo.list_all()
        assert len(logs) == 2

    async def test_batch_best_effort_mixed_results(self, app_client, log_repo):
        """One unknown provider should not block other targets."""
        resp = await app_client.post(
            "/notify/batch",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={
                "targets": [
                    {"provider": "mock", "identifier": "ok"},
                    {"provider": "ghost", "identifier": "bad"},
                ],
                "message": {"text": "hi"},
            },
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert results[0]["success"] is True
        assert results[1]["success"] is False
        logs = await log_repo.list_all()
        assert len(logs) == 2

    async def test_batch_empty_targets_returns_422(self, app_client):
        resp = await app_client.post(
            "/notify/batch",
            headers={"X-API-Key": NOTIFY_RAW_KEY},
            json={"targets": [], "message": {"text": "hi"}},
        )
        assert resp.status_code == 422

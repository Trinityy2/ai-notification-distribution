"""Tests for TelegramProvider.send() with mocked HTTP."""

import pytest
import respx
import httpx

from app.providers.telegram import TelegramProvider, TELEGRAM_API_BASE
from app.models.target import Target
from app.models.message import Message


class TestTelegramSend:
    @pytest.fixture
    def provider(self):
        return TelegramProvider(bot_token="test-token")

    @pytest.fixture
    def target(self):
        return Target(provider="telegram", identifier="123456")

    @respx.mock
    async def test_successful_send(self, provider, target):
        url = f"{TELEGRAM_API_BASE}/bottest-token/sendMessage"
        respx.post(url).mock(return_value=httpx.Response(200, json={"ok": True}))
        result = await provider.send(target, Message(text="hello"))
        assert result.success is True
        assert result.provider == "telegram"

    @respx.mock
    async def test_api_error_returns_failure(self, provider, target):
        url = f"{TELEGRAM_API_BASE}/bottest-token/sendMessage"
        respx.post(url).mock(return_value=httpx.Response(400, text="Bad Request"))
        result = await provider.send(target, Message(text="hello"))
        assert result.success is False
        assert "400" in result.error

    @respx.mock
    async def test_send_with_title_includes_title(self, provider, target):
        url = f"{TELEGRAM_API_BASE}/bottest-token/sendMessage"
        respx.post(url).mock(return_value=httpx.Response(200, json={"ok": True}))
        result = await provider.send(target, Message(text="body", title="Alert"))
        assert result.success is True

    @respx.mock
    async def test_network_error_returns_failure(self, provider, target):
        url = f"{TELEGRAM_API_BASE}/bottest-token/sendMessage"
        respx.post(url).mock(side_effect=httpx.ConnectError("Network error"))
        result = await provider.send(target, Message(text="hello"))
        assert result.success is False
        assert result.error is not None

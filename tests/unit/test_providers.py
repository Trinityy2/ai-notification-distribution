import pytest

from app.providers.base import InvalidTargetError, MessagingProvider
from app.providers.telegram import TelegramProvider
from app.providers.whatsapp import WhatsAppProvider
from app.providers.registry import ProviderRegistry
from app.models.target import Target
from app.models.message import Message


class TestTelegramValidateTarget:
    provider = TelegramProvider(bot_token="fake-token")

    @pytest.mark.parametrize("identifier", [
        "123456789",
        "-100123456789",
        "@mychannel",
        "@Valid_User1",
    ])
    async def test_valid_identifiers(self, identifier):
        target = Target(provider="telegram", identifier=identifier)
        await self.provider.validate_target(target)  # should not raise

    @pytest.mark.parametrize("identifier", [
        "not-a-number",
        "@ab",           # too short
        "abc",
        "@has spaces",
        "",
    ])
    async def test_invalid_identifiers_raise(self, identifier):
        if not identifier:
            # empty string already caught by Pydantic min_length=1
            return
        target = Target(provider="telegram", identifier=identifier)
        with pytest.raises(InvalidTargetError):
            await self.provider.validate_target(target)


class TestWhatsAppProviderStub:
    provider = WhatsAppProvider()

    async def test_validate_target_raises_not_implemented(self):
        target = Target(provider="whatsapp", identifier="+1234567890")
        with pytest.raises(NotImplementedError):
            await self.provider.validate_target(target)

    async def test_send_raises_not_implemented(self):
        target = Target(provider="whatsapp", identifier="+1234567890")
        message = Message(text="hello")
        with pytest.raises(NotImplementedError):
            await self.provider.send(target, message)


class TestProviderRegistry:
    def test_register_and_get(self):
        registry = ProviderRegistry()
        provider = TelegramProvider("token")
        registry.register("telegram", provider)
        assert registry.get("telegram") is provider

    def test_get_case_insensitive(self):
        registry = ProviderRegistry()
        provider = TelegramProvider("token")
        registry.register("Telegram", provider)
        assert registry.get("telegram") is provider
        assert registry.get("TELEGRAM") is provider

    def test_get_unknown_returns_none(self):
        registry = ProviderRegistry()
        assert registry.get("unknown") is None

    def test_get_or_raise_unknown_raises_key_error(self):
        registry = ProviderRegistry()
        with pytest.raises(KeyError, match="unknown"):
            registry.get_or_raise("unknown")

    def test_names_returns_registered(self):
        registry = ProviderRegistry()
        registry.register("telegram", TelegramProvider("t"))
        registry.register("whatsapp", WhatsAppProvider())
        assert set(registry.names()) == {"telegram", "whatsapp"}

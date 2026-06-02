from app.providers.base import MessagingProvider


class ProviderRegistry:
    """Maps provider names to MessagingProvider instances."""

    def __init__(self) -> None:
        self._providers: dict[str, MessagingProvider] = {}

    def register(self, name: str, provider: MessagingProvider) -> None:
        self._providers[name.lower()] = provider

    def get(self, name: str) -> MessagingProvider | None:
        return self._providers.get(name.lower())

    def get_or_raise(self, name: str) -> MessagingProvider:
        provider = self.get(name)
        if provider is None:
            available = ", ".join(self._providers.keys()) or "none"
            raise KeyError(
                f"Unknown provider '{name}'. Available providers: {available}."
            )
        return provider

    def names(self) -> list[str]:
        return list(self._providers.keys())

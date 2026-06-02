from app.models.message import Message
from app.models.result import SendResult
from app.models.target import Target
from app.providers.base import InvalidTargetError, MessagingProvider


class WhatsAppProvider(MessagingProvider):
    """Placeholder WhatsApp provider.

    Not yet implemented — awaiting selection of a WhatsApp Business API vendor.
    Add the concrete implementation here once a vendor is chosen.
    """

    async def validate_target(self, target: Target) -> None:
        raise NotImplementedError(
            "WhatsApp provider is not yet implemented. "
            "Implement validate_target() once a vendor is selected."
        )

    async def send(self, target: Target, message: Message) -> SendResult:
        raise NotImplementedError(
            "WhatsApp provider is not yet implemented. "
            "Implement send() once a vendor is selected."
        )

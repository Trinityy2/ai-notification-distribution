from abc import ABC, abstractmethod

from app.models.message import Message
from app.models.result import SendResult
from app.models.target import Target


class InvalidTargetError(ValueError):
    """Raised by validate_target() when a target identifier is malformed."""


class MessagingProvider(ABC):
    @abstractmethod
    async def send(self, target: Target, message: Message) -> SendResult:
        """Send *message* to *target*. Must not raise on delivery failure —
        return a SendResult with success=False instead."""

    async def validate_target(self, target: Target) -> None:
        """Validate the target identifier for this provider.

        Default implementation is a no-op.  Override to add provider-specific
        format checks.  Raise InvalidTargetError on invalid input.
        """

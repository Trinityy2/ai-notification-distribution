import re

import httpx

from app.models.message import Message
from app.models.result import SendResult
from app.models.target import Target
from app.providers.base import InvalidTargetError, MessagingProvider

# Matches numeric chat IDs (positive or negative) and @username handles
_CHAT_ID_RE = re.compile(r"^-?\d+$|^@[A-Za-z0-9_]{4,}$")

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramProvider(MessagingProvider):
    def __init__(self, bot_token: str) -> None:
        self._token = bot_token

    async def validate_target(self, target: Target) -> None:
        if not _CHAT_ID_RE.match(target.identifier):
            raise InvalidTargetError(
                f"Invalid Telegram identifier '{target.identifier}'. "
                "Expected a numeric chat ID (e.g. -100123456789) or "
                "@username (e.g. @mychannel)."
            )

    async def send(self, target: Target, message: Message) -> SendResult:
        text = f"*{message.title}*\n{message.text}" if message.title else message.text
        url = f"{TELEGRAM_API_BASE}/bot{self._token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    json={"chat_id": target.identifier, "text": text, "parse_mode": "Markdown"},
                )
            if resp.status_code == 200:
                return SendResult(success=True, provider="telegram", identifier=target.identifier)
            return SendResult(
                success=False,
                provider="telegram",
                identifier=target.identifier,
                error=f"Telegram API error {resp.status_code}: {resp.text}",
            )
        except Exception as exc:
            return SendResult(
                success=False,
                provider="telegram",
                identifier=target.identifier,
                error=str(exc),
            )

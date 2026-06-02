from datetime import datetime, timezone

from pydantic import BaseModel, Field


class SendResult(BaseModel):
    success: bool
    provider: str
    identifier: str
    error: str | None = None


class BatchSendResult(BaseModel):
    results: list[SendResult]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        return self.total - self.succeeded


class NotificationLog(BaseModel):
    id: str
    api_key_id: str
    target_provider: str
    target_identifier: str
    status: str  # "success" | "failure"
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

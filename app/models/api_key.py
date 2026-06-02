from datetime import datetime, timezone

from pydantic import BaseModel, Field


class APIKey(BaseModel):
    id: str
    name: str
    scopes: list[str]
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CreateKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = Field(..., min_length=1)


class CreateKeyResponse(BaseModel):
    id: str
    name: str
    scopes: list[str]
    raw_key: str  # shown exactly once; never stored


class UpdateKeyRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    scopes: list[str] | None = None
    is_active: bool | None = None

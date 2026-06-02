from pydantic import BaseModel, Field


class Target(BaseModel):
    provider: str = Field(..., min_length=1)
    identifier: str = Field(..., min_length=1)

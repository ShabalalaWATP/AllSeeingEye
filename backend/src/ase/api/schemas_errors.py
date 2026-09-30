"""Shared error response contract, including the safe support reference."""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: dict[str, str] | None = None
    request_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9-]{8,64}$")


class ErrorEnvelope(BaseModel):
    error: ErrorDetail

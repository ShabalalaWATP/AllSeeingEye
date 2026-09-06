"""Administrator activation and isolated source-test contracts."""

from pydantic import BaseModel, ConfigDict


class SourceActivationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


class SourceTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ok: bool
    fetched: int
    capped: bool
    message: str

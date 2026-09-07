"""Unsaved discovery accepts a write-only credential and an optional saved-key reference."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from ase.application.admin.llm_discovery import DiscoveryInput
from ase.domain.llm import MAX_API_KEY_LENGTH, normalise_base_url


class DraftModelDiscoveryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: Literal["openai_compatible"] = "openai_compatible"
    base_url: str = Field(min_length=8, max_length=512)
    api_key: SecretStr | None = Field(default=None, max_length=MAX_API_KEY_LENGTH)
    profile_id: UUID | None = None

    @field_validator("base_url")
    @classmethod
    def endpoint(cls, value: str) -> str:
        try:
            return normalise_base_url(value)
        except ValueError:
            raise ValueError("The model endpoint address is invalid.") from None

    def to_input(self) -> DiscoveryInput:
        key = self.api_key.get_secret_value().strip() if self.api_key else ""
        return DiscoveryInput(self.base_url, key or None, self.profile_id)

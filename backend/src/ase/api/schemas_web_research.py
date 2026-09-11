"""Generated web context is exposed separately from frozen primary evidence."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.web_research import WebResearchStatus


class WebCitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    title: str
    start_index: int = Field(ge=0, le=6000)
    end_index: int = Field(ge=0, le=6000)


class WebResearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: WebResearchStatus
    explanation: str
    retrieved_at: datetime
    requested_model: str | None
    returned_model: str | None
    profile_id: UUID | None
    profile_revision: int | None
    synthesis: str = Field(max_length=6000)
    citations: list[WebCitationOut] = Field(max_length=12)
    consulted_urls: list[str] = Field(max_length=20)
    tool_calls: int = Field(ge=0, le=3)
    request_count: int = Field(ge=0, le=1)
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: float
    policy_version: str
    notice: str

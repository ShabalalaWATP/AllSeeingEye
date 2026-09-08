"""Private input upload receipts; extracted passages are not exposed as a listing API."""

import base64
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.application.ports.research_inputs import InputPreviewFrame, ResearchInputReceipt


class ResearchInputPreviewOut(BaseModel):
    seconds: float = Field(ge=0, le=600)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    png_base64: str = Field(max_length=1_398_104)


class ResearchInputOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    filename: str = Field(max_length=120)
    media_type: str = Field(max_length=120)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    imported_at: datetime
    expires_at: datetime
    event_count: int = Field(ge=1, le=200)
    extracted_characters: int = Field(ge=0, le=200_000)
    preview: str = Field(max_length=1000)
    limitations: list[str] = Field(max_length=20)
    parent_input_id: UUID | None = None
    previews: list[ResearchInputPreviewOut] = Field(default_factory=list, max_length=3)

    @classmethod
    def from_receipt(
        cls, receipt: ResearchInputReceipt, frames: tuple[InputPreviewFrame, ...] = ()
    ) -> "ResearchInputOut":
        return cls.model_validate(
            {
                **asdict(receipt),
                "previews": [
                    {
                        "seconds": frame.seconds,
                        "sha256": frame.sha256,
                        "png_base64": base64.b64encode(frame.png).decode("ascii"),
                    }
                    for frame in frames
                ],
            }
        )

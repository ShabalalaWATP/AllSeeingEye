"""Explicit original-retention consent and inert asset metadata."""

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.original_assets import AssetStatus, OriginalAsset, OriginalAssetRequest


class OriginalAssetReserveIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version_number: int = Field(ge=1)
    evidence_label: str = Field(min_length=1, max_length=40)
    filename: str = Field(min_length=1, max_length=120)
    media_type: str = Field(min_length=1, max_length=160)
    permitted_use: str = Field(min_length=1, max_length=1000)
    byte_count: int = Field(ge=1, le=8 * 1024 * 1024)
    retention_days: int = Field(default=30, ge=1, le=90)

    def to_domain(self) -> OriginalAssetRequest:
        return OriginalAssetRequest(**self.model_dump())


class OriginalAssetOut(BaseModel):
    id: UUID
    report_id: UUID
    report_version_id: UUID
    version_number: int
    evidence_label: str
    source_id: str
    event_id: str
    sha256: str
    byte_count: int
    filename: str
    media_type: str
    permitted_use: str
    owner_id: UUID
    team_id: UUID | None
    uploader_id: UUID
    created_at: datetime
    expires_at: datetime
    reservation_expires_at: datetime
    status: AssetStatus
    transitioned_at: datetime | None

    @classmethod
    def build(cls, asset: OriginalAsset) -> "OriginalAssetOut":
        return cls.model_validate(asdict(asset))


class OriginalAssetListOut(BaseModel):
    items: list[OriginalAssetOut]

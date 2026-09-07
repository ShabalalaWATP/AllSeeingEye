"""Deliberately retained, hash-matched originals anchored to frozen evidence."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

MAX_ASSET_BYTES = 8 * 1024 * 1024
MAX_PERSONAL_BYTES = 64 * 1024 * 1024
MAX_TEAM_BYTES = 256 * 1024 * 1024
MAX_GLOBAL_BYTES = 1024 * 1024 * 1024
MAX_PERSONAL_RECORDS = 64
MAX_TEAM_RECORDS = 256
MAX_GLOBAL_RECORDS = 4096
MAX_PENDING_UPLOADS = 2
MAX_SELECTED_ASSETS = 20
MAX_EXPORT_ASSET_BYTES = 24 * 1024 * 1024
AssetStatus = Literal["reserved", "uploading", "active", "deleted", "expired"]


@dataclass(frozen=True, slots=True)
class OriginalAsset:
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
    status: AssetStatus = "reserved"
    transitioned_at: datetime | None = None
    session_family_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class OriginalAssetContent:
    asset: OriginalAsset
    content: bytes


@dataclass(frozen=True, slots=True)
class OriginalAssetRequest:
    version_number: int
    evidence_label: str
    filename: str
    media_type: str
    permitted_use: str
    byte_count: int
    retention_days: int = 30

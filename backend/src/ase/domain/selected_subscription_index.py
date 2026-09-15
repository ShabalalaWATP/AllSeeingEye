"""Validated, metadata-only input for a selected subscription research index."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime

_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _key(value: str, name: str, maximum: int) -> None:
    if type(value) is not str or not 1 <= len(value) <= maximum or not _KEY.fullmatch(value):
        raise ValueError(f"{name} must be a bounded public identifier")


def _utc(value: datetime | None, name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class SelectedMetadata:
    """Public metadata only. The caller must have reviewed the source's retention terms."""

    source_id: str
    item_key: str
    origin_key: str
    source_version: str
    title: str
    content_sha256: str
    policy_id: str
    retention_days: int
    retrieved_at: datetime
    published_at: datetime | None = None
    observed_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        for name, maximum in (
            ("source_id", 100),
            ("item_key", 200),
            ("origin_key", 300),
            ("source_version", 128),
            ("policy_id", 100),
        ):
            _key(getattr(self, name), name, maximum)
        if type(self.title) is not str or not 1 <= len(self.title) <= 300:
            raise ValueError("title must be 1 to 300 characters")
        if any(ord(char) < 32 and char not in "\t\n" for char in self.title):
            raise ValueError("title contains control characters")
        if type(self.content_sha256) is not str or not _SHA256.fullmatch(self.content_sha256):
            raise ValueError("content_sha256 must be lowercase SHA-256")
        if type(self.retention_days) is not int or not 1 <= self.retention_days <= 400:
            raise ValueError("retention_days must be 1 to 400")
        for name in ("retrieved_at", "published_at", "observed_at", "updated_at"):
            value = _utc(getattr(self, name), name)
            if name == "retrieved_at" and value is None:
                raise ValueError("retrieved_at is required")
            object.__setattr__(self, name, value)

    @property
    def fingerprint(self) -> str:
        value = [
            self.source_id,
            self.item_key,
            self.origin_key,
            self.source_version,
            self.content_sha256,
        ]
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @property
    def stored_bytes(self) -> int:
        value = {
            field: getattr(self, field)
            for field in (
                "source_id",
                "item_key",
                "origin_key",
                "source_version",
                "title",
                "content_sha256",
                "policy_id",
                "retention_days",
            )
        }
        for field in ("retrieved_at", "published_at", "observed_at", "updated_at"):
            timestamp = getattr(self, field)
            value[field] = timestamp.isoformat() if timestamp is not None else None
        return len(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"))


@dataclass(frozen=True, slots=True)
class SelectedIndexLimits:
    """Deployments may lower these ceilings, never raise them through an API request."""

    max_age_days: int = 400
    owner_records: int = 50_000
    owner_bytes: int = 256 * 1024 * 1024
    aggregate_bytes: int = 2 * 1024 * 1024 * 1024
    page_records: int = 100
    sources_per_subscription: int = 32

    def __post_init__(self) -> None:
        ceilings = (400, 50_000, 256 * 1024 * 1024, 2 * 1024 * 1024 * 1024, 100, 32)
        for field, ceiling in zip(self.__dataclass_fields__, ceilings, strict=True):
            value = getattr(self, field)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(f"{field} must be within the configured ceiling")

"""Small semantic index of current saved reports, never of live feed events."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from uuid import UUID

from ase.domain.llm import LlmProfile
from ase.domain.report_records import ReportRecord, ReportVersion

MAX_REPORTS = 1_000
MAX_DIMENSIONS = 4_096
MAX_TEXT_CHARS = 6_000
INDEX_BATCH = 8


def profile_fingerprint(profile: LlmProfile) -> str:
    """Key rotation and sampling settings do not change an embedding space."""
    value = f"{profile.id}\n{profile.base_url}\n{profile.model}"
    return hashlib.sha256(value.encode()).hexdigest()


def report_text(record: ReportRecord, version: ReportVersion) -> str:
    return "\n".join([record.title, *version.body.texts()])[:MAX_TEXT_CHARS]


def checked_vector(value: object) -> tuple[float, ...]:
    """Reject non-numeric, zero, non-finite and excessively large vectors."""
    if not isinstance(value, (list, tuple)) or not 1 <= len(value) <= MAX_DIMENSIONS:
        raise ValueError("Invalid embedding dimensions.")
    if any(type(item) not in (int, float) for item in value):
        raise ValueError("Invalid embedding value.")
    vector = tuple(float(item) for item in value)
    magnitude = math.hypot(*vector)
    if not math.isfinite(magnitude) or magnitude == 0:
        raise ValueError("Invalid embedding magnitude.")
    return tuple(item / magnitude for item in vector)


def cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions differ.")
    return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=True))))


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: tuple[tuple[float, ...], ...]
    latency_ms: float
    prompt_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class IndexedReport:
    report_id: UUID
    version: int
    fingerprint: str
    vector: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class SearchStatus:
    available: bool
    indexed: int
    total: int
    limit: int = MAX_REPORTS
    batch_size: int = INDEX_BATCH


@dataclass(frozen=True, slots=True)
class SearchHit:
    report: ReportRecord
    score: float


@dataclass(frozen=True, slots=True)
class SearchResult:
    items: tuple[SearchHit, ...]
    indexed: int
    total: int

"""Bounded warning identities, separate from the human-readable citation sample.

Only a length-delimited source/ID hash and an eligibility expiry are retained.
The 128-bit SHA-256 prefix has negligible, rather than impossible, collision risk.
Keep identities across rule edits for the maximum supported seven-day window.
"""

import hashlib
import struct
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ase.domain.events import Event

MAX_CONSUMED_PER_RULE = 350_000
MAX_CONSUMED_TOTAL = 1_000_000
CONSUMED_RETENTION = timedelta(days=7)
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
MAGIC = b"ASEC\x01"
RECORD = struct.Struct(">16sq")
Identity = tuple[bytes, int]


def instant(value: datetime) -> int:
    delta = value - EPOCH
    return (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds


MIN_INSTANT = instant(datetime.min.replace(tzinfo=UTC))
MAX_INSTANT = instant(datetime.max.replace(tzinfo=UTC))
RETENTION_MICROSECONDS = int(CONSUMED_RETENTION.total_seconds()) * 1_000_000


def digest(event: Event) -> bytes:
    source, identifier = event.source_id.encode("utf-8"), event.id.encode("utf-8")
    encoded = len(source).to_bytes(8, "big") + source + identifier
    return hashlib.sha256(encoded).digest()[:16]


def identity(event: Event, published: datetime) -> Identity:
    return digest(event), min(MAX_INSTANT, instant(published) + RETENTION_MICROSECONDS)


@dataclass(frozen=True, slots=True)
class ConsumedEvidence:
    identities: frozenset[bytes] = frozenset()
    legacy_before: datetime | None = None
    unavailable: str | None = None


EMPTY_CONSUMED = ConsumedEvidence()


def encode(entries: dict[bytes, int]) -> bytes:
    if len(entries) > MAX_CONSUMED_PER_RULE:
        raise ValueError("Consumed evidence exceeds the per-rule bound")
    if any(
        len(key) != 16 or not MIN_INSTANT <= expiry <= MAX_INSTANT
        for key, expiry in entries.items()
    ):
        raise ValueError("Invalid consumed evidence identity or expiry")
    return MAGIC + b"".join(RECORD.pack(key, expiry) for key, expiry in sorted(entries.items()))


def decode(data: bytes, count: int) -> dict[bytes, int]:
    if (
        not 0 <= count <= MAX_CONSUMED_PER_RULE
        or len(data) != len(MAGIC) + count * RECORD.size
        or not data.startswith(MAGIC)
    ):
        raise ValueError("Invalid consumed evidence version, size or count")
    entries: dict[bytes, int] = {}
    for key, expiry in RECORD.iter_unpack(data[len(MAGIC) :]):
        if key in entries or not MIN_INSTANT <= expiry <= MAX_INSTANT:
            raise ValueError("Invalid consumed evidence identity or expiry")
        entries[key] = expiry
    return entries


def active(entries: dict[bytes, int], now: datetime) -> dict[bytes, int]:
    # Warning windows include their lower boundary, so expiry is strictly before now.
    cutoff = instant(now)
    return {key: expiry for key, expiry in entries.items() if expiry >= cutoff}

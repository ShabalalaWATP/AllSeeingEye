"""Disposable gzip JSON-lines snapshot of the live store (ADR 0022).

The first line is a header, then one public event per line, then a trailer with the
event count and an HMAC-SHA256 over every earlier line, keyed by a secret the API
already holds, so a file written by anyone else is refused as a whole. Writes go to a
private temporary sibling that is flushed to disk and atomically renamed over the
previous file, so a failure leaves that file intact. Loading refuses symbolic links,
non-regular files, oversized, damaged, unsigned or wrongly signed input and unknown
versions, ignoring the whole file; invalid event records are skipped.
"""

from __future__ import annotations

import contextlib
import glob
import gzip
import hashlib
import heapq
import hmac
import json
import os
import stat
import tempfile
import zlib
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import IO, Any

import structlog

from ase.adapters.store.snapshot_codec import event_from_record, event_to_record
from ase.application.ports.live_snapshot import SnapshotLoad
from ase.domain.events import Event

log = structlog.get_logger(__name__)

FORMAT = "ase-live-store"
VERSION = 1
# Source geometry alone may reach 5 MiB, so one event line may be several MiB.
MAX_LINE_BYTES = 8 * 1024 * 1024
_READ_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_BINARY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
)


class _Rejected(Exception):
    """The whole file is unusable or unsafe. The message is safe to log."""


class _CappedWriter:
    """Counts compressed bytes on their way to disk and refuses to pass the cap."""

    def __init__(self, target: IO[bytes], limit: int) -> None:
        self._target, self._limit, self._size = target, limit, 0

    def write(self, data: bytes) -> int:
        self._size += len(data)
        if self._size > self._limit:
            raise _Rejected("snapshot exceeds the size cap")
        return self._target.write(data)

    def flush(self) -> None:
        self._target.flush()


class GzipSnapshotFile:
    """One replace-in-place file for a single API process (ADR 0022)."""

    def __init__(
        self,
        path: Path,
        *,
        key: bytes,
        max_bytes: int,
        max_decompressed_bytes: int,
        max_events: int,
    ) -> None:
        if len(key) < 32:
            raise ValueError("The snapshot signing key must be at least 32 bytes.")
        self._path = path
        self._key = key
        self._max_bytes = max_bytes
        self._max_decompressed = max_decompressed_bytes
        self._max_events = max_events

    def read(self) -> SnapshotLoad:
        self._remove_stale_temporaries()
        try:
            return self._read()
        except FileNotFoundError:
            return SnapshotLoad()
        except _Rejected as exc:
            reason = str(exc)
        except (OSError, EOFError, zlib.error, ValueError, RecursionError):
            # Includes truncated or corrupt gzip data and undecodable JSON lines.
            reason = "snapshot is unreadable or damaged"
        log.warning("live_snapshot.ignored", reason=reason)
        return SnapshotLoad()

    def write(self, events: Sequence[Event], saved_at: datetime) -> bool:
        try:
            written, skipped = self._write(events, saved_at)
        except _Rejected as exc:
            log.warning("live_snapshot.not_saved", reason=str(exc))
            return False
        except (OSError, ValueError) as exc:
            log.warning("live_snapshot.not_saved", reason=type(exc).__name__)
            return False
        log.info("live_snapshot.saved", events=written, skipped=skipped)
        return True

    def _read(self) -> SnapshotLoad:
        if self._path.is_symlink():
            raise _Rejected("symbolic link refused")
        descriptor = os.open(self._path, _READ_FLAGS)
        with os.fdopen(descriptor, "rb") as raw:
            status = os.fstat(raw.fileno())
            if not stat.S_ISREG(status.st_mode):
                raise _Rejected("snapshot is not a regular file")
            if status.st_size > self._max_bytes:
                raise _Rejected("snapshot exceeds the size cap")
            with gzip.GzipFile(fileobj=raw, mode="rb") as stream:
                return self._decode(stream)

    def _decode(self, stream: gzip.GzipFile) -> SnapshotLoad:
        remaining = self._max_decompressed

        def next_record() -> Any:
            nonlocal remaining, pending
            line = stream.readline(MAX_LINE_BYTES + 1)
            remaining -= len(line)
            if remaining < 0:
                raise _Rejected("snapshot exceeds the decompressed size cap")
            if not line.endswith(b"\n"):
                raise _Rejected("snapshot is truncated or has an oversized line")
            # Every line except the trailer is signed: sign the previous line once this
            # one shows it was not the trailer.
            if pending is not None:
                signature.update(pending)
            pending = line
            return json.loads(line.decode("utf-8"), parse_constant=_reject_constant)

        signature = hmac.new(self._key, digestmod=hashlib.sha256)
        pending: bytes | None = None
        header = next_record()
        if not isinstance(header, dict) or set(header) != {"format", "version", "saved_at"}:
            raise _Rejected("snapshot header is not recognised")
        if header["format"] != FORMAT or header["version"] != VERSION:
            raise _Rejected("snapshot format or version is not supported")
        if datetime.fromisoformat(str(header["saved_at"])).utcoffset() is None:
            raise _Rejected("snapshot header time has no timezone")
        events: dict[str, Event] = {}
        lines = skipped = 0
        while not isinstance(record := next_record(), dict) or "format" not in record:
            lines += 1
            if lines > self._max_events:
                raise _Rejected("snapshot holds too many events")
            try:
                event = event_from_record(record)
            except ValueError:
                skipped += 1
                continue
            if event.id in events:
                skipped += 1
            else:
                events[event.id] = event
        count = record.get("events")
        if set(record) != {"format", "events", "mac"} or record["format"] != FORMAT:
            raise _Rejected("snapshot trailer is not recognised")
        mac = record["mac"]
        if not isinstance(mac, str) or not hmac.compare_digest(mac, signature.hexdigest()):
            raise _Rejected("snapshot signature does not match")
        if type(count) is not int or count != lines:
            raise _Rejected("snapshot event count does not match")
        # Reading to the end also verifies the gzip checksum and length.
        if stream.read(1):
            raise _Rejected("snapshot has data after its trailer")
        return SnapshotLoad(tuple(events.values()), skipped)

    def _write(self, events: Sequence[Event], saved_at: datetime) -> tuple[int, int]:
        directory = self._path.parent
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self._path.is_symlink():
            raise _Rejected("symbolic link refused")
        if self._path.exists() and not self._path.is_file():
            raise _Rejected("snapshot path is not a regular file")
        # mkstemp creates the file exclusively with owner-only permissions on POSIX.
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{self._path.name}.", suffix=".tmp", dir=directory
        )
        try:
            with os.fdopen(descriptor, "wb") as raw:
                capped = _CappedWriter(raw, self._max_bytes)
                with gzip.GzipFile(
                    filename="", mode="wb", fileobj=capped, compresslevel=6, mtime=0
                ) as stream:
                    counts = self._encode(stream, events, saved_at)
                raw.flush()
                os.fsync(raw.fileno())
            # rename replaces a link itself rather than writing through it.
            os.replace(temporary, self._path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
            raise
        _sync_directory(directory)
        return counts

    def _encode(
        self, stream: gzip.GzipFile, events: Sequence[Event], saved_at: datetime
    ) -> tuple[int, int]:
        size = 0
        signature = hmac.new(self._key, digestmod=hashlib.sha256)

        def emit(line: bytes, *, signed: bool = True) -> None:
            nonlocal size
            size += len(line)
            if size > self._max_decompressed:
                raise _Rejected("snapshot exceeds the decompressed size cap")
            if signed:
                signature.update(line)
            stream.write(line)

        emit(_line({"format": FORMAT, "version": VERSION, "saved_at": saved_at.isoformat()}))
        selected: Sequence[Event] = events
        if len(events) > self._max_events:
            # Between prunes the store may briefly exceed its caps; keep the newest.
            selected = heapq.nlargest(self._max_events, events, key=lambda e: e.observed_at)
        written = skipped = 0
        for event in selected:
            try:
                line = _line(event_to_record(event))
            except (TypeError, ValueError):
                skipped += 1
                continue
            if len(line) > MAX_LINE_BYTES:
                skipped += 1
                continue
            emit(line)
            written += 1
        trailer = {"format": FORMAT, "events": written, "mac": signature.hexdigest()}
        emit(_line(trailer), signed=False)
        return written, skipped + len(events) - len(selected)

    def _remove_stale_temporaries(self) -> None:
        """A crash during a save can leave one temporary sibling behind."""
        pattern = f".{glob.escape(self._path.name)}.*.tmp"
        with contextlib.suppress(OSError):
            for stale in self._path.parent.glob(pattern):
                with contextlib.suppress(OSError):
                    stale.unlink()


def _line(record: dict[str, Any]) -> bytes:
    text = json.dumps(record, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return (text + "\n").encode("utf-8")


def _reject_constant(name: str) -> None:
    raise ValueError(f"Snapshot JSON may not contain {name}")


def _sync_directory(directory: Path) -> None:
    """Make the rename durable where the platform allows opening a directory."""
    if os.name != "posix":
        return
    with contextlib.suppress(OSError):
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

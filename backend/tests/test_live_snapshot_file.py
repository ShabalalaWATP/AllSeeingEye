"""The disposable live-store snapshot file: format, bounds, safety and atomic replacement."""

from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
from datetime import timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from ase.adapters.store import snapshot_file
from ase.adapters.store.snapshot_codec import EVENT_FIELDS, event_to_record
from ase.adapters.store.snapshot_file import FORMAT, GzipSnapshotFile
from ase.domain.events import Category, Event
from ase.domain.evidence_geometry import EvidenceGeometry, LocationRole
from ase.domain.observation import ObservationMetadata
from ase.domain.project import ProjectMetadata
from ase.domain.source_dates import resolve_source_date
from ase.domain.text_transformations import TextTransformation
from feeds_helpers import NOW, make_event

KIB = 1024
SAVED_AT = NOW.isoformat()


KEY = b"k" * 32


def snapshot(path: Path, *, key: bytes = KEY, **limits: int) -> GzipSnapshotFile:
    values = {"max_bytes": 1024 * KIB, "max_decompressed_bytes": 4096 * KIB, "max_events": 1_000}
    return GzipSnapshotFile(path, key=key, **(values | limits))


PROJECT: dict[str, Any] = {
    "dataset_id": "aiddata-geogcdf",
    "release_id": "v3.0.1",
    "project_id": "35756",
    "source_sha256": "a" * 64,
    "recipient_iso3": "LAO",
    "reported_status": "Completion",
    "precision": "precise",
    "attribution": "AidData",
    "data_licence": "ODC-By-1.0",
    "geometry_licence": "ODbL-1.0",
    "limitations": "Derived geometry.",
    "commitment_year": 2011,
    "completion_year": 2012,
}
TRANSFORMATION: dict[str, Any] = {
    "field": "summary",
    "original_text": "A summary",
    "transformed_text": "Transliterated",
    "kind": "transliteration",
    "source_language": "fa",
    "target_language": "en",
    "origin": "operator",
    "method": "Operator transcription v1",
    "source_script": "Arab",
    "target_script": "Latn",
}


def rich_event() -> Event:
    ring = [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]]
    return make_event("rich", category=Category.NEWS, severity=None).with_changes(
        language="fa",
        title_en="English title",
        country_iso="IR",
        tags=frozenset({"alpha", "beta"}),
        severity=2,
        story_id="story-1",
        attributes=MappingProxyType(
            {"count": 3, "ratio": 0.25, "flag": True, "note": "x", "empty": None}
        ),
        geometry=EvidenceGeometry(
            json.dumps({"type": "Polygon", "coordinates": [ring]}),
            LocationRole.REPORTED_AREA,
            "approximate",
            "provider_coordinates",
            "test_source",
            "Synthetic fixture",
        ),
        observation=ObservationMetadata(
            NOW - timedelta(days=1), "collection", "item", "Metadata only", NOW, 7.5
        ),
        project=ProjectMetadata(**PROJECT),
        transformations=(TextTransformation(**TRANSFORMATION),),
        source_dates=(resolve_source_date("2026-09-04", "date", "gregorian"),),
    )


def gzip_lines(*records: Any, sign: bool = True) -> bytes:
    """Lines as written; the first trailer-shaped record is signed like a real file."""
    lines = [(item if isinstance(item, str) else json.dumps(item)) + "\n" for item in records]
    signature = hmac.new(KEY, digestmod=hashlib.sha256)
    for index, item in enumerate(records):
        if sign and isinstance(item, dict) and item.get("format") == FORMAT and "events" in item:
            # A signature the test supplies wins, so forged values can be exercised.
            lines[index] = json.dumps({"mac": signature.hexdigest()} | item) + "\n"
            break
        signature.update(lines[index].encode("utf-8"))
    return gzip.compress("".join(lines).encode("utf-8"))


def header(**changes: Any) -> dict[str, Any]:
    return {"format": FORMAT, "version": 1, "saved_at": SAVED_AT} | changes


def trailer(count: int) -> dict[str, Any]:
    return {"format": FORMAT, "events": count}


def test_round_trip_preserves_every_public_field(tmp_path: Path) -> None:
    rich = rich_event()
    undated = make_event("undated").with_changes(published_at=None, point=None)
    events = [rich, make_event("plain"), undated]
    assert set(event_to_record(rich)) == EVENT_FIELDS
    file = snapshot(tmp_path / "live.jsonl.gz")
    assert file.write(events, NOW)
    loaded = file.read()
    assert loaded.skipped == 0
    assert list(loaded.events) == events
    restored = loaded.events[0]
    assert type(restored.severity) is int
    assert dict(restored.attributes) == dict(rich.attributes)
    assert restored.geometry == rich.geometry
    assert restored.transformations == rich.transformations


def test_file_is_versioned_gzip_json_lines_with_a_trailer(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl.gz"
    assert snapshot(path).write([make_event("a"), make_event("b")], NOW)
    lines = gzip.decompress(path.read_bytes()).decode("utf-8").splitlines()
    assert json.loads(lines[0]) == header()
    last = json.loads(lines[-1])
    assert re.fullmatch(r"[0-9a-f]{64}", last.pop("mac"))
    assert last == trailer(2)
    assert len(lines) == 4
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_missing_file_restores_nothing(tmp_path: Path) -> None:
    loaded = snapshot(tmp_path / "absent.jsonl.gz").read()
    assert loaded.events == ()


EVENT = event_to_record(make_event("a"))
DAMAGED = {
    "not gzip": b"not a gzip stream at all",
    "empty": b"",
    "wrong version": gzip_lines(header(version=2), EVENT, trailer(1)),
    "wrong format": gzip_lines(header(format="other"), EVENT, trailer(1)),
    "extra header field": gzip_lines(header(owner="x"), EVENT, trailer(1)),
    "naive header time": gzip_lines(header(saved_at="2026-09-05T00:00:00"), trailer(0)),
    "missing trailer": gzip_lines(header(), EVENT),
    "count mismatch": gzip_lines(header(), EVENT, trailer(2)),
    "boolean count": gzip_lines(header(), EVENT, trailer(1) | {"events": True}),
    "odd trailer": gzip_lines(header(), EVENT, trailer(1) | {"extra": 1}),
    "data after trailer": gzip_lines(header(), EVENT, trailer(1), EVENT),
    "bad json line": gzip_lines(header(), "{not json", trailer(1)),
    "non-finite constant": gzip_lines(header(), '{"severity": NaN}', trailer(1)),
    "concatenated member": gzip_lines(header(), trailer(0)) + gzip_lines(EVENT),
    "unsigned trailer": gzip_lines(header(), EVENT, trailer(1), sign=False),
    "wrong signature": gzip_lines(header(), EVENT, trailer(1) | {"mac": "0" * 64}),
    "non-text signature": gzip_lines(header(), EVENT, trailer(1) | {"mac": 7}),
}


@pytest.mark.parametrize("name", sorted(DAMAGED))
def test_damaged_or_foreign_files_are_ignored(tmp_path: Path, name: str) -> None:
    path = tmp_path / "live.jsonl.gz"
    path.write_bytes(DAMAGED[name])
    assert snapshot(path).read().events == ()


def test_a_file_signed_with_another_key_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl.gz"
    assert snapshot(path, key=b"o" * 32).write([make_event("forged")], NOW)
    assert snapshot(path).read().events == ()


def test_an_edited_event_line_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl.gz"
    assert snapshot(path).write([make_event("a"), make_event("b")], NOW)
    lines = gzip.decompress(path.read_bytes()).decode("utf-8").splitlines(keepends=True)
    lines[1] = json.dumps(json.loads(lines[1]) | {"title": "Fabricated"}) + "\n"
    path.write_bytes(gzip.compress("".join(lines).encode("utf-8")))
    assert snapshot(path).read().events == ()


def test_a_short_signing_key_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        snapshot(tmp_path / "live.jsonl.gz", key=b"short")


def test_truncated_file_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl.gz"
    assert snapshot(path).write([make_event(str(key)) for key in range(20)], NOW)
    data = path.read_bytes()
    for cut in (10, len(data) // 2, len(data) - 4):
        path.write_bytes(data[:cut])
        assert snapshot(path).read().events == ()


def test_corrupted_checksum_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl.gz"
    assert snapshot(path).write([make_event("a")], NOW)
    data = bytearray(path.read_bytes())
    data[-8] ^= 0xFF
    path.write_bytes(bytes(data))
    assert snapshot(path).read().events == ()


def test_oversized_inputs_are_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "live.jsonl.gz"
    assert snapshot(path).write([make_event(str(key)) for key in range(50)], NOW)
    size = path.stat().st_size
    assert snapshot(path, max_bytes=size - 1).read().events == ()
    assert snapshot(path, max_decompressed_bytes=2 * KIB).read().events == ()
    assert snapshot(path, max_events=49).read().events == ()
    monkeypatch.setattr(snapshot_file, "MAX_LINE_BYTES", 64)
    assert snapshot(path).read().events == ()


def test_invalid_or_unknown_records_are_skipped(tmp_path: Path) -> None:
    good = make_event("good")
    records = [
        event_to_record(good),
        event_to_record(make_event("private")) | {"owner_id": "someone"},
        event_to_record(make_event("unknown")) | {"category": "unknown"},
        {key: value for key, value in EVENT.items() if key != "observed_at"},
        event_to_record(make_event("naive")) | {"observed_at": "2026-09-05T00:00:00"},
        event_to_record(good),
        ["not", "an", "object"],
    ]
    path = tmp_path / "live.jsonl.gz"
    path.write_bytes(gzip_lines(header(), *records, trailer(len(records))))
    loaded = snapshot(path).read()
    assert loaded.events == (good,)
    assert loaded.skipped == len(records) - 1


def test_symbolic_links_are_refused(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere.jsonl.gz"
    assert snapshot(target).write([make_event("a")], NOW)
    link = tmp_path / "live.jsonl.gz"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("This platform or account cannot create symbolic links")
    assert snapshot(link).read().events == ()
    before = target.read_bytes()
    assert not snapshot(link).write([make_event("b")], NOW)
    assert link.is_symlink()
    assert target.read_bytes() == before


def test_symbolic_link_checks_run_before_file_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "live.jsonl.gz"
    assert snapshot(path).write([make_event("a")], NOW)
    before = path.read_bytes()
    monkeypatch.setattr(Path, "is_symlink", lambda self: self == path)
    assert snapshot(path).read().events == ()
    assert not snapshot(path).write([make_event("b")], NOW)
    assert path.read_bytes() == before


def test_directory_in_place_of_the_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl.gz"
    path.mkdir()
    assert snapshot(path).read().events == ()
    assert not snapshot(path).write([make_event("a")], NOW)
    assert list(tmp_path.iterdir()) == [path]


def test_failed_replace_keeps_the_previous_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "live.jsonl.gz"
    first = make_event("first")
    assert snapshot(path).write([first], NOW)

    def refuse(*_args: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(snapshot_file.os, "replace", refuse)
    assert not snapshot(path).write([make_event("second")], NOW)
    monkeypatch.undo()
    assert snapshot(path).read().events == (first,)
    assert sorted(tmp_path.iterdir()) == [path]


def test_size_caps_skip_the_write_rather_than_truncate(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl.gz"
    first = make_event("first")
    assert snapshot(path).write([first], NOW)
    # Random titles do not compress, so the compressed cap is reached mid-stream.
    noisy = [make_event(str(key), title=secrets.token_hex(250)) for key in range(40)]
    assert not snapshot(path, max_bytes=4 * KIB).write(noisy, NOW)
    assert not snapshot(path, max_decompressed_bytes=4 * KIB).write(noisy, NOW)
    assert snapshot(path).read().events == (first,)
    assert sorted(tmp_path.iterdir()) == [path]


def test_unencodable_events_are_skipped_on_write(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl.gz"
    broken = make_event("nan").with_changes(attributes=MappingProxyType({"value": float("nan")}))
    kept = make_event("kept")
    assert snapshot(path).write([broken, kept], NOW)
    assert snapshot(path).read().events == (kept,)


def test_writer_keeps_the_newest_events_within_the_event_cap(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl.gz"
    events = [make_event(str(age), observed_at=NOW - timedelta(hours=age)) for age in range(3)]
    assert snapshot(path, max_events=2).write(events, NOW)
    assert {event.id for event in snapshot(path).read().events} == {
        events[0].id,
        events[1].id,
    }


def test_stale_temporary_siblings_are_removed_on_load(tmp_path: Path) -> None:
    path = tmp_path / "live.jsonl.gz"
    stale = tmp_path / ".live.jsonl.gz.abc123.tmp"
    stale.write_bytes(b"partial")
    unrelated = tmp_path / "keep.tmp"
    unrelated.write_bytes(b"other")
    snapshot(path).read()
    assert not stale.exists()
    assert unrelated.exists()

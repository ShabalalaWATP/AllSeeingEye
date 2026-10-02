"""Signed JSON-line parsing preserves rejection, skipping and concurrent reads."""

import gzip
import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from ase.adapters.store.snapshot_codec import event_to_record
from ase.adapters.store.snapshot_file import FORMAT, GzipSnapshotFile
from feeds_helpers import NOW, make_event
from test_live_snapshot_file import KEY, header, rich_event, snapshot


def signed_lines(path: Path, event_lines: list[bytes], *, header_prefix: bytes = b"") -> None:
    lines = [header_prefix + json.dumps(header()).encode() + b"\n", *event_lines]
    signature = hmac.new(KEY, b"".join(lines), hashlib.sha256).hexdigest()
    trailer = json.dumps({"format": FORMAT, "events": len(event_lines), "mac": signature})
    path.write_bytes(gzip.compress(b"".join(lines) + trailer.encode() + b"\n"))


def encoded(identifier: str) -> bytes:
    return json.dumps(event_to_record(make_event(identifier)), ensure_ascii=False).encode()


@pytest.mark.parametrize("padding", [b"", b" ", b"\t\r "])
def test_signed_json_accepts_standard_whitespace_without_changing_events(
    tmp_path: Path, padding: bytes
) -> None:
    path = tmp_path / "whitespace.gz"
    event = make_event("unicode").with_changes(title="Snowman \u2603 and embedded \ufeff mark")
    text = json.dumps(event_to_record(event), ensure_ascii=False).encode()
    signed_lines(path, [padding + text + padding + b"\n"])
    result = snapshot(path).read()
    assert result.events == (event,)
    assert result.skipped == 0


@pytest.mark.parametrize(
    "bad_line",
    [
        b"\xef\xbb\xbf" + encoded("bad") + b"\n",
        encoded("bad") + b" {}\n",
        b"{malformed}\n",
        b'{"title":"\xff"}\n',
        b'{"severity":NaN}\n',
        b'{"severity":Infinity}\n',
        b'{"severity":-Infinity}\n',
        b"\v{}\n",
    ],
    ids=["bom", "extra-data", "syntax", "utf8", "nan", "infinity", "negative-inf", "space"],
)
def test_json_or_unicode_failure_rejects_the_whole_signed_file(
    tmp_path: Path, bad_line: bytes
) -> None:
    path = tmp_path / "invalid.gz"
    signed_lines(path, [encoded("before") + b"\n", bad_line, encoded("after") + b"\n"])
    result = snapshot(path).read()
    assert result.events == ()
    assert result.skipped == 0


def test_leading_bom_in_signed_header_is_not_accepted(tmp_path: Path) -> None:
    path = tmp_path / "header.gz"
    signed_lines(path, [encoded("valid") + b"\n"], header_prefix=b"\xef\xbb\xbf")
    assert snapshot(path).read().events == ()


def test_numeric_overflow_remains_an_invalid_record_not_a_json_constant_failure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "overflow.gz"
    invalid = encoded("overflow").replace(b'"severity": 0.5', b'"severity": 1e999')
    signed_lines(path, [encoded("before") + b"\n", invalid + b"\n", encoded("after") + b"\n"])
    result = snapshot(path).read()
    assert result.events == (make_event("before"), make_event("after"))
    assert result.skipped == 1


@pytest.mark.parametrize("invalid", [b"null", b"42", b"[]", b'{"id":"incomplete"}'])
def test_valid_json_invalid_events_are_skipped_without_discarding_valid_records(
    tmp_path: Path, invalid: bytes
) -> None:
    path = tmp_path / "skipped.gz"
    signed_lines(path, [encoded("before") + b"\n", invalid + b"\n", encoded("after") + b"\n"])
    result = snapshot(path).read()
    assert result.events == (make_event("before"), make_event("after"))
    assert result.skipped == 1


def test_repeated_and_concurrent_reads_keep_complete_independent_results(tmp_path: Path) -> None:
    path = tmp_path / "concurrent.gz"
    file = snapshot(path)
    expected = [rich_event(), make_event("ordinary")]
    assert file.write(expected, NOW)
    barrier = Barrier(4)

    def read_together(_: int):
        barrier.wait(timeout=5)
        return file.read()

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(read_together, range(4)))
    assert all(result.events == tuple(expected) and result.skipped == 0 for result in results)
    assert file.read().events == tuple(expected)


def test_one_reader_cannot_share_signature_state_with_another_file(tmp_path: Path) -> None:
    first_path, second_path = tmp_path / "first.gz", tmp_path / "second.gz"
    first = snapshot(first_path)
    second = snapshot(second_path, key=b"s" * 32)
    assert first.write([make_event("first")], NOW)
    assert second.write([make_event("second")], NOW)

    def read(file: GzipSnapshotFile):
        return file.read()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(read, [first, second]))
    assert results[0].events == (make_event("first"),)
    assert results[1].events == (make_event("second"),)
    assert snapshot(second_path).read().events == ()

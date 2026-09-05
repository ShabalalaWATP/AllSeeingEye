"""Offline backup drills exercise real SQLite data without touching the development DB."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from backup_helpers import backup, bundle, create_backup, create_project, restore


def test_sqlite_roundtrip_preserves_reports_evidence_configuration_and_wal(tmp_path: Path) -> None:
    root, output, restored = tmp_path / "project", tmp_path / "backup", tmp_path / "restored"
    source = create_project(root)
    with closing(sqlite3.connect(source)) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("PRAGMA wal_autocheckpoint=0")
        live.execute("INSERT INTO reports VALUES ('r2', 'Latest committed report')")
        live.commit()
        assert Path(str(source) + "-wal").stat().st_size > 0
        assert create_backup(root, output) == 0
        # Source changes after the snapshot must not change the recovery point.
        live.execute("DELETE FROM reports WHERE id = 'r2'")
        live.commit()
    assert restore.main([str(output), "--verify-only"]) == 0
    assert restore.main([str(output), "--output", str(restored)]) == 0
    with closing(sqlite3.connect(restored / "database.sqlite3")) as database:
        assert database.execute("SELECT title FROM reports ORDER BY id").fetchall() == [
            ("Country brief",),
            ("Latest committed report",),
        ]
        assert database.execute("SELECT title FROM evidence").fetchone() == ("Frozen source",)
        assert database.execute("SELECT value FROM configuration").fetchone() == ("local-model",)
    assert (restored / "config/.env.example").read_bytes() == (root / ".env.example").read_bytes()
    assert not (output / "config/.env").exists()
    assert not (output / "live-cache.json").exists()
    assert not (output / "database.sqlite3-wal").exists()
    assert not (output / "database.sqlite3-shm").exists()


def test_secrets_require_explicit_flag_and_are_never_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, output, restored = tmp_path / "project", tmp_path / "backup", tmp_path / "restored"
    create_project(root)
    assert create_backup(root, output, secrets=True) == 0
    manifest = bundle.verify_bundle(output)
    assert manifest["includes_env"] is True
    assert restore.main([str(output), "--output", str(restored)]) == 0
    assert (restored / "config/.env").read_bytes() == (root / ".env").read_bytes()
    captured = capsys.readouterr()
    assert "private-fixture" not in captured.out + captured.err


def test_existing_backup_and_restore_destinations_are_untouched(tmp_path: Path) -> None:
    root, output = tmp_path / "project", tmp_path / "backup"
    source = create_project(root)
    assert create_backup(root, output) == 0
    original_backup = (output / "database.sqlite3").read_bytes()
    original_source = source.read_bytes()
    assert create_backup(root, output) == 1
    assert restore.main([str(output), "--output", str(root)]) == 1
    assert source.read_bytes() == original_source
    assert (output / "database.sqlite3").read_bytes() == original_backup
    assert not (root / "database.sqlite3").exists()


def test_hash_tampering_is_refused_before_target_creation(tmp_path: Path) -> None:
    root, output, restored = tmp_path / "project", tmp_path / "backup", tmp_path / "restored"
    create_project(root)
    assert create_backup(root, output) == 0
    with (output / "database.sqlite3").open("ab") as database:
        database.write(b"tampered")
    assert restore.main([str(output), "--output", str(restored)]) == 1
    assert not restored.exists()


def test_rehashed_corrupt_database_is_still_refused(tmp_path: Path) -> None:
    output = bundle.new_directory(tmp_path / "backup")
    (output / "database.sqlite3").write_bytes(b"not a database")
    bundle.write_manifest(output, "sqlite", include_secrets=False)
    with pytest.raises(bundle.BackupError, match="integrity"):
        bundle.verify_bundle(output)


def test_verification_never_creates_wal_sidecars(tmp_path: Path) -> None:
    output = bundle.new_directory(tmp_path / "backup")
    database_path = output / "database.sqlite3"
    with closing(sqlite3.connect(database_path)) as database:
        database.execute("PRAGMA journal_mode=WAL")
        database.execute("CREATE TABLE reports (id TEXT)")
        database.commit()
    bundle.write_manifest(output, "sqlite", include_secrets=False)
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    assert restore.main([str(output), "--verify-only"]) == 0
    assert {path.name: path.read_bytes() for path in output.iterdir()} == before


@pytest.mark.parametrize(
    "content",
    [
        b"not JSON",
        b"[]",
        b'{"version":true}',
        b'{"version":1,"backend":"sqlite","files":null}',
        b"[" * 1500 + b"]" * 1500,
    ],
    ids=["invalid-json", "wrong-root", "boolean-version", "missing-files", "deep-json"],
)
def test_malformed_manifests_fail_cleanly(tmp_path: Path, content: bytes) -> None:
    output = bundle.new_directory(tmp_path / "backup")
    (output / "manifest.json").write_bytes(content)
    assert restore.main([str(output), "--verify-only"]) == 1


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/absolute",
        "config/../../escape",
        "C:/escape",
        "config\\.env",
        "config/.env:stream",
        "unlisted.json",
    ],
)
def test_manifest_paths_are_allowlisted(tmp_path: Path, name: str) -> None:
    root, output = tmp_path / "project", tmp_path / "backup"
    create_project(root)
    assert create_backup(root, output) == 0
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["files"][0]["path"] = name
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(bundle.BackupError, match="Unexpected"):
        bundle.verify_bundle(output)


@pytest.mark.parametrize(
    "change",
    [
        "duplicate",
        "negative",
        "oversized",
        "hash",
        "env",
        "backend",
        "missing",
        "extra",
        "directory",
        "manifest_size",
    ],
)
def test_invalid_bundle_is_rejected(tmp_path: Path, change: str) -> None:
    root, output = tmp_path / "project", tmp_path / "backup"
    create_project(root)
    assert create_backup(root, output) == 0
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if change == "duplicate":
        manifest["files"].append(manifest["files"][0])
    elif change == "negative":
        manifest["files"][0]["size"] = -1
    elif change == "oversized":
        manifest["files"][0]["size"] = bundle.MAX_BYTES + 1
    elif change == "hash":
        manifest["files"][0]["sha256"] = "invalid"
    elif change == "env":
        manifest["includes_env"] = True
    elif change == "backend":
        manifest["backend"] = "mysql"
    elif change == "missing":
        (output / "database.sqlite3").unlink()
    elif change == "extra":
        (output / "extra").write_bytes(b"unexpected")
    elif change == "directory":
        (output / "extra").mkdir()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    if change == "manifest_size":
        manifest_path.write_bytes(b" " * (bundle.MANIFEST_LIMIT + 1))
    with pytest.raises(bundle.BackupError):
        bundle.verify_bundle(output)


@pytest.mark.parametrize("link_kind", ["is_symlink", "is_junction"])
def test_links_in_parent_paths_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link_kind: str
) -> None:
    linked = tmp_path / "linked"
    monkeypatch.setattr(Path, link_kind, lambda self: self == linked)
    with pytest.raises(bundle.BackupError, match="links and junctions"):
        bundle.safe_path(linked / "child" / "database.sqlite3", must_exist=False)


def test_missing_source_creates_no_database_and_existing_file_is_not_overwritten(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    assert create_backup(root, tmp_path / "backup") == 1
    assert not (root / "ase.db").exists()
    assert not (tmp_path / "backup/manifest.json").exists()
    file = tmp_path / "existing"
    file.write_bytes(b"keep")
    with pytest.raises(bundle.BackupError, match="already exists"):
        bundle.new_directory(file)
    assert file.read_bytes() == b"keep"


def test_size_limits_and_missing_output_parent(tmp_path: Path) -> None:
    path = tmp_path / "large"
    path.write_bytes(b"1234")
    with pytest.raises(bundle.BackupError, match="size limit"):
        bundle.digest(path, 3)
    with pytest.raises(bundle.BackupError, match="parent"):
        bundle.new_directory(tmp_path / "missing/backup")


def test_missing_env_is_an_error_only_when_requested(tmp_path: Path) -> None:
    root = tmp_path / "project"
    create_project(root)
    (root / ".env").unlink()
    assert create_backup(root, tmp_path / "without-env") == 0
    assert create_backup(root, tmp_path / "with-env", secrets=True) == 1


@pytest.mark.parametrize(
    "arguments", [["sqlite", "--output", "x"], ["postgres", "--output", "x", "--database", "x"]]
)
def test_backup_cli_rejects_ambiguous_database_selection(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        backup.main(arguments)
    assert error.value.code == 2


@pytest.mark.parametrize("arguments", [["x"], ["x", "--verify-only", "--output", "x"]])
def test_restore_cli_rejects_ambiguous_targets(arguments: list[str]) -> None:
    with pytest.raises(SystemExit) as error:
        restore.main(arguments)
    assert error.value.code == 2

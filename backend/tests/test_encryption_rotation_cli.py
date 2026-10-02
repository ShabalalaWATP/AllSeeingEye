"""Operator command refuses unsafe invocation and never echoes key material."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ase import cli_encryption
from ase.cli import app


def test_rotation_requires_explicit_maintenance_confirmation(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "rotate-encryption-key",
            "--old-key-file",
            str(tmp_path / "old"),
            "--new-key-file",
            str(tmp_path / "new"),
        ],
    )
    assert result.exit_code == 1
    assert "--maintenance-confirmed" in result.output


def test_rotation_reads_protected_files_and_reports_only_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old, new = "old-test-secret-" * 4, "new-test-secret-" * 4
    for name, key in (("old", old), ("new", new)):
        (tmp_path / name).write_text(key)
        (tmp_path / name).chmod(0o600)

    async def rotate(database_url: str, old_key: str, new_key: str) -> int:
        assert old_key == old and new_key == new
        assert database_url == "sqlite+aiosqlite:///disposable.db"
        return 9

    monkeypatch.setattr(cli_encryption, "_rotate", rotate)
    monkeypatch.setenv("ASE_ENV", "test")
    monkeypatch.setenv("ASE_DATABASE_URL", "sqlite+aiosqlite:///disposable.db")
    result = CliRunner().invoke(
        app,
        [
            "rotate-encryption-key",
            "--old-key-file",
            str(tmp_path / "old"),
            "--new-key-file",
            str(tmp_path / "new"),
            "--maintenance-confirmed",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Rotated 9" in result.output and old not in result.output and new not in result.output
    (tmp_path / "old").write_text("short")
    failed = CliRunner().invoke(
        app,
        [
            "rotate-encryption-key",
            "--old-key-file",
            str(tmp_path / "old"),
            "--new-key-file",
            str(tmp_path / "new"),
            "--maintenance-confirmed",
        ],
    )
    assert failed.exit_code == 1 and "short" not in failed.output

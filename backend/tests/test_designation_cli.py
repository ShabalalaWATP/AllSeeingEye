"""Host import commands accept explicit UTC dates and cannot overwrite snapshots."""

from pathlib import Path

from typer.testing import CliRunner

from ase.cli import app


def test_local_import_requires_timezone_and_preserves_immutable_destination(tmp_path: Path) -> None:
    source = tmp_path / "sdn.csv"
    source.write_bytes(b'1,"Example Fiction Ltd",-0-,-0-,-0-,-0-,-0-,-0-,-0-,-0-,-0-,-0-\n')
    base = [
        "import-designations",
        str(source),
        "--cache-dir",
        str(tmp_path / "cache"),
        "--authority",
        "ofac_sdn",
        "--version",
        "fixture",
        "--licence",
        "Synthetic fixture",
    ]
    runner = CliRunner()
    failed = runner.invoke(app, [*base, "--published-at", "2026-09-06"])
    assert failed.exit_code == 1
    success = runner.invoke(app, [*base, "--published-at", "2026-09-06T12:00:00Z"])
    assert success.exit_code == 0, success.output
    target = tmp_path / "cache/ofac_sdn-fixture.json"
    original = target.read_bytes()
    repeated = runner.invoke(app, [*base, "--published-at", "2026-09-06T12:00:00Z"])
    assert repeated.exit_code == 1 and target.read_bytes() == original

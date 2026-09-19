"""PostgreSQL command contracts are tested entirely through a mock subprocess boundary."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from backup_helpers import backup, bundle, create_project, postgres, restore


@pytest.fixture
def commands(monkeypatch: pytest.MonkeyPatch) -> Mock:
    def execute(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if "printenv" in command:
            return subprocess.CompletedProcess(command, 0, stdout=b"ase_operator\nase_live\n")
        if "pg_dump" in command:
            kwargs["stdout"].write(b"PGDMP-fixture-dump")
        return subprocess.CompletedProcess(command, 0)

    runner = Mock(side_effect=execute)
    monkeypatch.setattr(postgres.subprocess, "run", runner)
    return runner


def test_compose_backup_and_new_database_restore_commands(tmp_path: Path, commands: Mock) -> None:
    root, output, recovered = tmp_path / "project", tmp_path / "backup", tmp_path / "recovered"
    create_project(root)
    key = tmp_path / "backup.key"
    key.write_bytes(b"k" * 32)
    compose = root / "docker-compose.yml"
    assert (
        backup.main(
            [
                "postgres",
                "--output",
                str(output),
                "--project-root",
                str(root),
                "--compose-file",
                str(compose),
                "--authentication-key-file",
                str(key),
            ]
        )
        == 0
    )
    assert bundle.verify_bundle(output)["backend"] == "postgres"
    count = commands.call_count
    assert restore.main([str(output), "--verify-only"]) == 0
    assert commands.call_count == count  # Offline verification never requires Docker.
    assert (
        restore.main(
            [
                str(output),
                "--output",
                str(recovered),
                "--target-database",
                "ase_drill",
                "--compose-file",
                str(compose),
                "--authentication-key-file",
                str(key),
            ]
        )
        == 0
    )
    invoked = [call.args[0] for call in commands.call_args_list]
    prefix = ["docker", "compose", "--file", str(compose), "exec", "-T", "db"]
    assert invoked == [
        [*prefix, "printenv", "POSTGRES_USER", "POSTGRES_DB"],
        [
            *prefix,
            "pg_dump",
            "--username",
            "ase_operator",
            "--dbname",
            "ase_live",
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "--no-password",
        ],
        [*prefix, "printenv", "POSTGRES_USER", "POSTGRES_DB"],
        [*prefix, "pg_restore", "--list"],
        [
            *prefix,
            "createdb",
            "--username",
            "ase_operator",
            "--no-password",
            "--maintenance-db=postgres",
            "--template=template0",
            "ase_drill",
        ],
        [
            *prefix,
            "pg_restore",
            "--username",
            "ase_operator",
            "--no-password",
            "--dbname",
            "ase_drill",
            "--no-owner",
            "--no-acl",
            "--single-transaction",
            "--exit-on-error",
        ],
    ]
    assert (recovered / "config/.env.example").exists()
    for call in commands.call_args_list:
        assert call.kwargs.get("shell", False) is False
        assert call.kwargs["stderr"] == subprocess.DEVNULL
        assert call.kwargs["timeout"] == 600
        assert "POSTGRES_PASSWORD" not in call.args[0]
        assert "--clean" not in call.args[0]


@pytest.mark.parametrize(
    "target",
    [
        "ase",
        "ASE",
        "postgres",
        "template0",
        "template1",
        "--clean",
        "host=attacker",
        "bad;DROP",
        "x" * 64,
    ],
)
def test_unsafe_and_live_targets_never_run_a_command(
    tmp_path: Path, commands: Mock, target: str
) -> None:
    database = postgres.ComposeDatabase(tmp_path / "compose.yml", "ase", "ase")
    with pytest.raises(bundle.BackupError):
        postgres.restore_postgres(database, tmp_path / "not-opened.dump", target)
    commands.assert_not_called()


def test_existing_database_failure_does_not_restore_or_drop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = postgres.ComposeDatabase(tmp_path / "compose.yml", "ase", "ase")
    dump = tmp_path / "database.dump"
    dump.write_bytes(b"PGDMP-fixture")
    runner = Mock(
        side_effect=[
            subprocess.CompletedProcess([], 0),
            subprocess.CalledProcessError(1, ["createdb"]),
        ]
    )
    monkeypatch.setattr(postgres.subprocess, "run", runner)
    with pytest.raises(bundle.BackupError, match="command failed"):
        postgres.restore_postgres(database, dump, "ase_existing")
    assert runner.call_count == 2
    assert runner.call_args_list[0].args[0][-2:] == ["pg_restore", "--list"]
    assert "createdb" in runner.call_args_list[1].args[0]


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError("secret driver detail"),
        subprocess.TimeoutExpired("driver", 600),
        subprocess.CalledProcessError(1, ["driver"], stderr=b"secret"),
    ],
)
def test_errors_are_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    error: Exception,
) -> None:
    root, output = tmp_path / "project", tmp_path / "backup"
    create_project(root)
    key = tmp_path / "backup.key"
    key.write_bytes(b"k" * 32)
    monkeypatch.setattr(postgres.subprocess, "run", Mock(side_effect=error))
    assert (
        backup.main(
            [
                "postgres",
                "--output",
                str(output),
                "--project-root",
                str(root),
                "--compose-file",
                str(root / "docker-compose.yml"),
                "--authentication-key-file",
                str(key),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "command failed" in captured.err
    assert "secret" not in captured.out + captured.err
    assert not (output / "manifest.json").exists()


@pytest.mark.parametrize("environment", [b"one\n", b"user\nhost=bad\n", b"--option\ndb\n"])
def test_compose_environment_is_validated_before_dump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, environment: bytes
) -> None:
    compose = tmp_path / "compose.yml"
    compose.write_text("services: {}", encoding="utf-8")
    runner = Mock(return_value=subprocess.CompletedProcess([], 0, stdout=environment))
    monkeypatch.setattr(postgres.subprocess, "run", runner)
    with pytest.raises(bundle.BackupError):
        postgres.connect_compose(compose)
    assert runner.call_count == 1


def test_postgres_header_is_checked_without_a_database(tmp_path: Path) -> None:
    output = bundle.new_directory(tmp_path / "backup")
    (output / "database.dump").write_bytes(b"not-postgres")
    bundle.write_manifest(output, "postgres", include_secrets=False)
    assert restore.main([str(output), "--verify-only"]) == 1


def test_selected_compose_configuration_is_preserved(tmp_path: Path, commands: Mock) -> None:
    root, output = tmp_path / "project", tmp_path / "backup"
    create_project(root)
    custom = tmp_path / "custom-compose.yml"
    custom.write_text("services: {db: {image: example}}", encoding="utf-8")
    key = tmp_path / "backup.key"
    key.write_bytes(b"k" * 32)
    assert (
        backup.main(
            [
                "postgres",
                "--output",
                str(output),
                "--project-root",
                str(root),
                "--compose-file",
                str(custom),
                "--authentication-key-file",
                str(key),
            ]
        )
        == 0
    )
    assert (output / "config/docker-compose.yml").read_bytes() == custom.read_bytes()


def test_restore_requires_explicit_postgres_target(tmp_path: Path, commands: Mock) -> None:
    output = bundle.new_directory(tmp_path / "backup")
    (output / "database.dump").write_bytes(b"PGDMP-fixture")
    bundle.write_manifest(output, "postgres", include_secrets=False)
    recovered = tmp_path / "recovered"
    assert restore.main([str(output), "--output", str(recovered)]) == 1
    assert not recovered.exists()
    commands.assert_not_called()


def test_postgres_restore_rejects_rehashed_tampering_before_any_command(
    tmp_path: Path, commands: Mock
) -> None:
    output = bundle.new_directory(tmp_path / "backup")
    dump = output / "database.dump"
    dump.write_bytes(b"PGDMP-original")
    bundle.write_manifest(output, "postgres", include_secrets=False)
    key = tmp_path / "backup.key"
    key.write_bytes(b"k" * 32)
    bundle.write_manifest_signature(output, bundle.authentication_key(key))
    original_signature = (output / bundle.SIGNATURE_FILE).read_bytes()

    dump.write_bytes(b"PGDMP-attacker-controlled")
    (output / "manifest.json").unlink()
    (output / bundle.SIGNATURE_FILE).unlink()
    bundle.write_manifest(output, "postgres", include_secrets=False)
    (output / bundle.SIGNATURE_FILE).write_bytes(original_signature)

    recovered = tmp_path / "recovered"
    assert (
        restore.main(
            [
                str(output),
                "--output",
                str(recovered),
                "--target-database",
                "ase_drill",
                "--authentication-key-file",
                str(key),
            ]
        )
        == 1
    )
    assert not recovered.exists()
    commands.assert_not_called()


def test_postgres_restore_authenticates_the_exact_manifest_bytes_once(
    tmp_path: Path, commands: Mock, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = bundle.new_directory(tmp_path / "backup")
    (output / "database.dump").write_bytes(b"PGDMP-original")
    bundle.write_manifest(output, "postgres", include_secrets=False)
    key = tmp_path / "backup.key"
    key.write_bytes(b"k" * 32)
    bundle.write_manifest_signature(output, bundle.authentication_key(key))
    manifest_path = output / "manifest.json"
    original_open = Path.open
    reads = 0

    def counted_open(path: Path, *args: object, **kwargs: object):
        nonlocal reads
        if path == manifest_path and args and args[0] == "rb":
            reads += 1
            if reads > 1:
                raise AssertionError("manifest bytes were read again after authentication")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", counted_open)
    recovered = tmp_path / "recovered"
    assert (
        restore.main(
            [
                str(output),
                "--output",
                str(recovered),
                "--target-database",
                "ase_drill",
                "--authentication-key-file",
                str(key),
            ]
        )
        == 0
    )
    assert reads == 1

"""Scheduled backup orchestration, retention and archive safety without Docker."""

import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backup_archive
import scheduled_backup
from backup_bundle import BackupError

KEY_TEXT = "k" * 48


class Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = self.tmp / "backups"
        self.root.mkdir()
        self.key = self.tmp / "encryption.key"
        self.key.write_text(KEY_TEXT)
        self.key.chmod(0o600)
        self.auth = self.tmp / "auth.key"
        self.auth.write_bytes(b"a" * 32)


class ArchiveRulesTests(Workspace):
    def test_names_sort_chronologically_in_utc(self) -> None:
        moment = datetime(2026, 9, 25, 3, 17, 1, tzinfo=UTC)
        self.assertEqual(
            backup_archive.archive_name(moment), "scheduled-20260925T031701Z"
        )

    def test_prune_keeps_newest_and_ignores_everything_else(self) -> None:
        names = [f"scheduled-2026092{day}T031701Z.tar.gpg" for day in range(1, 6)]
        for name in [*names, "postgres-20260901_031701", "notes.tar.gpg"]:
            (self.root / name).write_text("x")
        removed = backup_archive.prune(self.root, 3)
        self.assertEqual(removed, names[:2])
        left = sorted(path.name for path in self.root.iterdir())
        self.assertEqual(
            left, sorted(["notes.tar.gpg", *names[2:], "postgres-20260901_031701"])
        )

    def test_prune_refuses_tiny_retention(self) -> None:
        with self.assertRaises(BackupError):
            backup_archive.prune(self.root, 2)

    def test_encryption_key_rules(self) -> None:
        self.assertEqual(backup_archive.encryption_key(self.key), self.key)
        short = self.tmp / "short.key"
        short.write_text("too short")
        with self.assertRaises(BackupError):
            backup_archive.encryption_key(short)
        with self.assertRaises(BackupError):
            backup_archive.encryption_key(self.tmp / "missing.key")

    @unittest.skipUnless(os.name == "posix", "POSIX permission bits")
    def test_encryption_key_must_be_private(self) -> None:
        self.key.chmod(0o640)
        with self.assertRaises(BackupError):
            backup_archive.encryption_key(self.key)

    def test_heartbeat_and_offsite_inputs_are_constrained(self) -> None:
        self.assertEqual(
            backup_archive.heartbeat_url("https://hc-ping.com/abc/"),
            "https://hc-ping.com/abc",
        )
        self.assertIsNone(backup_archive.heartbeat_url(None))
        for bad in (
            "http://hc-ping.com/abc",
            "https://user@hc-ping.com/x",
            "file:///etc",
        ):
            with self.assertRaises(BackupError):
                backup_archive.heartbeat_url(bad)
        for bad in ("-e sh@host:x", "host:path", "u@host:path;rm"):
            with self.assertRaises(BackupError):
                backup_archive.push_offsite(self.key, bad, 22)

    def test_extract_accepts_one_bundle_and_refuses_traversal(self) -> None:
        bundle = self.tmp / "scheduled-20260925T031701Z"
        bundle.mkdir()
        (bundle / "manifest.json").write_text("{}")
        good = self.tmp / "good.tar"
        backup_archive.pack(bundle, good)
        out = self.tmp / "out"
        out.mkdir()
        self.assertEqual(backup_archive.extract(good, out), out / bundle.name)
        self.assertTrue((out / bundle.name / "manifest.json").is_file())
        for name in (
            "../escape.txt",
            "scheduled-20260925T031701Z/../../escape.txt",
            "other",
        ):
            bad = self.tmp / "bad.tar"
            with tarfile.open(bad, "w") as archive:
                info = tarfile.TarInfo(name)
                info.size = 1
                archive.addfile(info, io.BytesIO(b"x"))
            with self.assertRaises(BackupError):
                backup_archive.extract(bad, self.tmp / "out2")
            bad.unlink()


def fake_backup(arguments: list[str]) -> int:
    output = Path(arguments[arguments.index("--output") + 1])
    output.mkdir()
    (output / "manifest.json").write_text("{}")
    return 0


def fake_encrypt(tar_path: Path, _key: Path, output: Path) -> None:
    shutil.copyfile(tar_path, output)


class RunTests(Workspace):
    def options(self, *extra: str) -> list[str]:
        return [
            "run",
            "--root",
            str(self.root),
            "--authentication-key-file",
            str(self.auth),
            "--encryption-key-file",
            str(self.key),
            "--keep",
            "3",
            *extra,
        ]

    def run_with(self, *, backup_code: int = 0, digest: str | None = None) -> int:
        with (
            mock.patch.object(scheduled_backup.backup, "main", side_effect=fake_backup)
            if backup_code == 0
            else mock.patch.object(
                scheduled_backup.backup, "main", return_value=backup_code
            ),
            mock.patch.object(scheduled_backup, "encrypt", side_effect=fake_encrypt),
            mock.patch.object(
                scheduled_backup,
                "decrypted_sha256",
                side_effect=lambda path, _key: digest or backup_archive.sha256(path),
            ),
            mock.patch.object(scheduled_backup, "ping", return_value=True) as ping,
        ):
            code = scheduled_backup.main(self.options())
        self.ping = ping
        return code

    def status(self) -> dict[str, object]:
        return json.loads((self.root / "status.json").read_text())

    def test_success_leaves_one_encrypted_archive_and_a_status(self) -> None:
        self.assertEqual(self.run_with(), 0)
        found = backup_archive.archives(self.root)
        self.assertEqual(len(found), 1)
        status = self.status()
        self.assertEqual(status["result"], "ok")
        self.assertEqual(status["archive"], found[0].name)
        self.assertEqual(status["last_success"], status["attempted"])
        self.assertFalse(
            [p for p in self.root.iterdir() if p.name.startswith(".work-")]
        )
        self.ping.assert_called_once_with(None, failed=False)

    def test_failed_backup_reports_and_keeps_previous_success(self) -> None:
        (self.root / "status.json").write_text(json.dumps({"last_success": "earlier"}))
        self.assertEqual(self.run_with(backup_code=1), 1)
        status = self.status()
        self.assertEqual(status["result"], "failed")
        self.assertEqual(status["last_success"], "earlier")
        self.assertEqual(backup_archive.archives(self.root), [])
        self.ping.assert_called_once_with(None, failed=True)

    def test_round_trip_mismatch_discards_the_archive(self) -> None:
        self.assertEqual(self.run_with(digest="0" * 64), 1)
        self.assertEqual(backup_archive.archives(self.root), [])
        self.assertIn("round-trip", str(self.status()["message"]))

    def test_missing_root_is_refused(self) -> None:
        shutil.rmtree(self.root)
        self.assertEqual(scheduled_backup.main(self.options()), 1)


class DrillAndRecoveryTests(Workspace):
    def fake_decrypt(self, _archive: Path, _key: Path, tar_path: Path) -> None:
        bundle = self.tmp / "src" / "scheduled-20260925T031701Z"
        bundle.mkdir(parents=True, exist_ok=True)
        (bundle / "manifest.json").write_text("{}")
        with tarfile.open(tar_path, "w") as archive:
            archive.add(bundle, arcname=bundle.name)

    def drill(self, restore_code: int) -> int:
        arguments = ["drill", "--root", str(self.root)]
        arguments += ["--authentication-key-file", str(self.auth)]
        arguments += ["--encryption-key-file", str(self.key)]
        with (
            mock.patch.object(
                scheduled_backup, "decrypt", side_effect=self.fake_decrypt
            ),
            mock.patch.object(
                scheduled_backup.restore, "main", return_value=restore_code
            ) as main,
            mock.patch.object(scheduled_backup, "ping", return_value=True) as ping,
        ):
            code = scheduled_backup.main(arguments)
        self.restore_main, self.ping = main, ping
        return code

    def test_drill_needs_an_archive(self) -> None:
        self.assertEqual(self.drill(0), 1)
        self.ping.assert_called_once_with(None, failed=True)

    def test_drill_authenticates_the_newest_archive(self) -> None:
        (self.root / "scheduled-20260924T031701Z.tar.gpg").write_text("old")
        (self.root / "scheduled-20260925T031701Z.tar.gpg").write_text("new")
        self.assertEqual(self.drill(0), 0)
        arguments = self.restore_main.call_args.args[0]
        self.assertTrue(arguments[0].endswith("scheduled-20260925T031701Z"))
        self.assertIn("--verify-only", arguments)
        self.assertIn(str(self.auth), arguments)
        self.assertFalse(
            [p for p in self.root.iterdir() if p.name.startswith(".drill-")]
        )

    def test_drill_reports_a_failed_verification(self) -> None:
        (self.root / "scheduled-20260925T031701Z.tar.gpg").write_text("new")
        self.assertEqual(self.drill(1), 1)
        self.ping.assert_called_once_with(None, failed=True)

    def test_decrypt_recovers_into_a_new_directory_only(self) -> None:
        archive = self.root / "scheduled-20260925T031701Z.tar.gpg"
        archive.write_text("x")
        output = self.tmp / "recovered"
        arguments = ["decrypt", str(archive), "--encryption-key-file", str(self.key)]
        with mock.patch.object(
            scheduled_backup, "decrypt", side_effect=self.fake_decrypt
        ):
            self.assertEqual(
                scheduled_backup.main([*arguments, "--output", str(output)]), 0
            )
            self.assertTrue(
                (output / "scheduled-20260925T031701Z" / "manifest.json").is_file()
            )
            self.assertFalse((output / ".archive.tar").exists())
            self.assertEqual(
                scheduled_backup.main([*arguments, "--output", str(output)]), 1
            )


@unittest.skipUnless(shutil.which("gpg"), "GnuPG is not installed")
class GnuPGRoundTripTests(Workspace):
    def test_encrypt_then_decrypt_restores_identical_bytes(self) -> None:
        bundle = self.tmp / "scheduled-20260925T031701Z"
        bundle.mkdir()
        (bundle / "database.dump").write_bytes(os.urandom(4096))
        expected = backup_archive.pack(bundle, self.tmp / "b.tar")
        encrypted = self.tmp / "b.tar.gpg"
        backup_archive.encrypt(self.tmp / "b.tar", self.key, encrypted)
        self.assertNotEqual(backup_archive.sha256(encrypted), expected)
        self.assertEqual(backup_archive.decrypted_sha256(encrypted, self.key), expected)
        wrong = self.tmp / "wrong.key"
        wrong.write_text("w" * 48)
        wrong.chmod(0o600)
        with self.assertRaises(BackupError):
            backup_archive.decrypted_sha256(encrypted, wrong)


if __name__ == "__main__":
    unittest.main()

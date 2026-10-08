"""Deployment pruning keeps what a rollback needs and touches nothing else.

Uses temporary state directories and a fake process runner; no Docker or Git.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prune_deployments as prune

REVISIONS = [f"{index:x}" * 40 for index in range(1, 11)]  # 1111... to aaaa...
# The checkout HEAD has image tags but no release record (a manual rollout, say).
HEAD = REVISIONS[-1]


class FakeDocker:
    """Answers the inventory commands and records every removal request."""

    def __init__(self, tags: list[tuple[str, str, str]], in_use: list[str]) -> None:
        self.tags = tags
        self.in_use = in_use
        self.removed: list[str] = []
        self.fail_on: set[str] = set()

    def __call__(self, *args: str) -> str:
        if args[:2] == ("git", "-C"):
            return HEAD
        if args[:3] == ("docker", "image", "ls"):
            return "\n".join("\t".join(row) for row in self.tags)
        if args[:2] == ("docker", "ps"):
            return "\n".join(f"container-{index}" for index in range(len(self.in_use)))
        if args[:2] == ("docker", "inspect"):
            return "\n".join(self.in_use)
        if args[:3] == ("docker", "image", "rm"):
            if args[3] in self.fail_on:
                raise prune.PruneError("Operation failed: docker image")
            self.removed.append(args[3])
            return ""
        raise AssertionError(f"Unexpected command: {args}")


class Workspace(unittest.TestCase):
    def setUp(self) -> None:
        self.state = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.state, ignore_errors=True)
        (self.state / "deployment.lock").write_text("")
        (self.state / "manual-rollout-0014.log").write_text("operator")
        (self.state / "env-backup-20261001").write_text("operator")
        self.records: list[Path] = []
        # Releases 1 to 8, each deploying REVISIONS[n] over REVISIONS[n - 1].
        for index in range(1, 9):
            self.records.append(
                self.record(index, succeeded=index not in (7, 8), stamp=1_000 + index)
            )
        rows = []
        for index, revision in enumerate(REVISIONS):
            rows.append(("ase-api", f"release-{revision}", f"sha256:api{index}"))
            rows.append(("ase-web", f"release-{revision}", f"sha256:web{index}"))
            rows.append(("ase-parser", f"rollback-{revision}", f"sha256:api{index}"))
        rows.append(("ase-api", "latest", "sha256:api8"))
        rows.append(("postgis", f"release-{REVISIONS[0]}", "sha256:other"))
        self.docker = FakeDocker(rows, ["sha256:api8", "sha256:web8", "sha256:api0"])

    def record(self, index: int, *, succeeded: bool, stamp: int) -> Path:
        target, previous = REVISIONS[index], REVISIONS[index - 1]
        path = self.state / f"{target[:12]}-abc{index}_xyz"[: 12 + 1 + 8]
        path.mkdir()
        (path / "backup").mkdir()
        (path / "backup" / "database.dump").write_text("dump")
        release = path / "release.json"
        release.write_text(json.dumps({"previous": previous, "target": target}))
        os.utime(release, (stamp, stamp))
        if succeeded:
            (path / "success").write_text(target + "\n")
        return path

    def main(self, *arguments: str) -> tuple[int, str]:
        output = io.StringIO()
        with (
            patch.object(prune, "run", side_effect=self.docker),
            patch.object(
                prune, "deployment_lock", return_value=contextlib.nullcontext()
            ) as lock,
            contextlib.redirect_stdout(output),
            contextlib.redirect_stderr(output),
        ):
            code = prune.main(
                ["--state-dir", str(self.state), "--checkout", "repo", *arguments]
            )
        self.lock = lock
        return code, output.getvalue()

    def operator_files_untouched(self) -> None:
        for name in (
            "deployment.lock",
            "manual-rollout-0014.log",
            "env-backup-20261001",
        ):
            self.assertTrue((self.state / name).is_file(), name)


class PlanTests(Workspace):
    def test_dry_run_is_the_default_and_removes_nothing(self) -> None:
        code, output = self.main("--keep", "3")
        self.assertEqual(code, 0)
        self.assertEqual(self.docker.removed, [])
        self.assertTrue(all(path.is_dir() for path in self.records))
        self.assertIn("Dry run: nothing was removed", output)
        self.lock.assert_not_called()

    def test_keeps_newest_releases_latest_success_head_and_used_images(self) -> None:
        code, _ = self.main("--keep", "2", "--apply")
        self.assertEqual(code, 0)
        self.lock.assert_called_once_with(self.state)
        # Releases 7 and 8 failed, so release 6 (the newest success) is kept too.
        kept = {path.name for path in self.records[5:]}
        left = {path.name for path in self.state.iterdir()}
        self.assertTrue(kept <= left)
        self.assertFalse({path.name for path in self.records[:5]} & left)
        kept_revisions = set(REVISIONS[5:])  # targets and previous of releases 6 to 8
        for reference in self.docker.removed:
            self.assertNotIn(reference.rsplit("-", 1)[1], kept_revisions)
        # Revision 0 is old but a container still uses its API image.
        self.assertNotIn(f"ase-api:release-{REVISIONS[0]}", self.docker.removed)
        self.assertNotIn(f"ase-parser:rollback-{REVISIONS[0]}", self.docker.removed)
        self.assertIn(f"ase-web:release-{REVISIONS[0]}", self.docker.removed)
        self.assertIn(f"ase-api:release-{REVISIONS[1]}", self.docker.removed)
        self.assertNotIn("ase-api:latest", self.docker.removed)
        self.assertFalse([ref for ref in self.docker.removed if "postgis" in ref])
        self.operator_files_untouched()

    def test_head_is_kept_even_without_a_record(self) -> None:
        self.main("--keep", "2", "--apply")
        self.assertTrue(self.docker.removed)
        self.assertFalse([ref for ref in self.docker.removed if HEAD in ref])

    def test_retention_below_two_is_refused(self) -> None:
        for value in ("1", "0", "-3", "two"):
            with (
                self.subTest(value=value),
                self.assertRaises(SystemExit),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                prune.parser().parse_args(["--keep", value])
        with self.assertRaises(prune.PruneError):
            prune.plan([], [], set(), HEAD, 1)

    def test_dry_run_and_apply_are_exclusive(self) -> None:
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            prune.parser().parse_args(["--dry-run", "--apply"])


class SafetyTests(Workspace):
    def test_only_controller_records_are_recognised(self) -> None:
        candidates = {
            "deployment.lock": None,
            "manual-0123456789ab-abcd1234": None,
            "env-0123456789ab-abcd1234": None,
        }
        for name in candidates:
            self.assertIsNone(prune.read_record(self.state / name))
        stray = self.state / "0123456789ab-notvalid!"
        stray.mkdir()
        self.assertIsNone(prune.read_record(stray))
        mismatched = self.state / "0123456789ab-abcd1234"
        mismatched.mkdir()
        body = {"previous": REVISIONS[0], "target": REVISIONS[1]}
        (mismatched / "release.json").write_text(json.dumps(body))
        self.assertIsNone(prune.read_record(mismatched))
        broken = self.state / f"{REVISIONS[1][:12]}-broken12"
        broken.mkdir()
        (broken / "release.json").write_text("{not json")
        self.assertIsNone(prune.read_record(broken))
        self.assertIsNotNone(prune.read_record(self.records[0]))

    def test_linked_records_are_never_followed(self) -> None:
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        body = {"previous": REVISIONS[0], "target": REVISIONS[1]}
        (outside / "release.json").write_text(json.dumps(body))
        link = self.state / f"{REVISIONS[1][:12]}-linked12"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Creating links needs extra privileges here.")
        self.assertIsNone(prune.read_record(link))
        self.main("--keep", "2", "--apply")
        self.assertTrue((outside / "release.json").is_file())

    def test_record_with_leftover_worktree_is_left_in_place(self) -> None:
        (self.records[0] / "source").mkdir()
        code, output = self.main("--keep", "2", "--apply")
        self.assertEqual(code, 0)
        self.assertTrue(self.records[0].is_dir())
        self.assertIn("still holds a source worktree", output)

    def test_inventory_failure_removes_nothing(self) -> None:
        def failing(*args: str) -> str:
            if args[:2] == ("docker", "ps"):
                raise prune.PruneError("Operation failed: docker ps")
            return self.docker(*args)

        with (
            patch.object(prune, "run", side_effect=failing),
            patch.object(
                prune, "deployment_lock", return_value=contextlib.nullcontext()
            ),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            code = prune.main(
                ["--state-dir", str(self.state), "--checkout", "x", "--apply"]
            )
        self.assertEqual(code, 1)
        self.assertEqual(self.docker.removed, [])
        self.assertTrue(all(path.is_dir() for path in self.records))

    def test_failed_untag_is_reported_and_others_continue(self) -> None:
        self.docker.fail_on = {f"ase-web:release-{REVISIONS[1]}"}
        code, output = self.main("--keep", "2", "--apply")
        self.assertEqual(code, 1)
        self.assertIn("Could not remove", output)
        self.assertIn(f"ase-api:release-{REVISIONS[1]}", self.docker.removed)
        self.operator_files_untouched()

    @unittest.skipUnless(os.name == "posix", "the deployment lock is Linux-only")
    def test_lock_is_required_never_created_and_honoured(self) -> None:
        import fcntl

        lock = self.state / "deployment.lock"
        with (
            lock.open("a") as held,
            self.assertRaisesRegex(prune.PruneError, "in progress"),
        ):
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with prune.deployment_lock(self.state):
                pass
        lock.unlink()
        with (
            self.assertRaisesRegex(prune.PruneError, "No deployment lock"),
            prune.deployment_lock(self.state),
        ):
            pass
        self.assertFalse(lock.exists())

    def test_missing_state_directory_is_refused(self) -> None:
        shutil.rmtree(self.state)
        code, _ = self.main()
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

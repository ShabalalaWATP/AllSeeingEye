"""Deployment lifecycle regressions using temporary storage and mocked processes."""

import json
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deploy_vps as deploy

OLD = "a" * 40
NEW = "b" * 40
OLD_IMAGES = {
    "api": "sha256:old-api",
    "parser": "sha256:old-api",
    "web": "sha256:old-web",
}
NEW_IMAGES = {
    "api": "sha256:new-api",
    "parser": "sha256:new-api",
    "web": "sha256:new-web",
}


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        key = self.directory / "backup.key"
        key.touch()
        self.stack.enter_context(patch.object(deploy, "KEY", key))
        self.stack.enter_context(patch.object(deploy, "STATE", self.directory))
        self.disk = self.stack.enter_context(
            patch.object(
                deploy.shutil,
                "disk_usage",
                return_value=SimpleNamespace(free=7 * 1024**3),
            )
        )
        self.mocks = {}
        for name in (
            "require_latest",
            "require_clean",
            "require_compatible",
            "git",
            "run",
            "current_images",
            "build",
            "backup",
            "rollout",
            "wait_healthy",
        ):
            self.mocks[name] = self.stack.enter_context(patch.object(deploy, name))
        self.mocks["git"].return_value = OLD
        self.mocks["current_images"].return_value = OLD_IMAGES
        self.mocks["build"].return_value = NEW_IMAGES

    def test_build_failure_never_backs_up_or_cuts_over(self):
        self.mocks["build"].side_effect = deploy.DeploymentError("build failed")
        with self.assertRaisesRegex(deploy.DeploymentError, "build failed"):
            deploy.deploy(NEW)
        self.mocks["backup"].assert_not_called()
        self.mocks["rollout"].assert_not_called()
        self.assertFalse(list(self.directory.glob("*/success")))

    def test_backup_failure_never_cuts_over(self):
        self.mocks["backup"].side_effect = deploy.DeploymentError("backup failed")
        with self.assertRaisesRegex(deploy.DeploymentError, "backup failed"):
            deploy.deploy(NEW)
        self.mocks["build"].assert_called_once()
        self.mocks["rollout"].assert_not_called()
        self.assertFalse(list(self.directory.glob("*/success")))

    def test_preflight_does_not_build_backup_or_restart(self):
        deploy.deploy(NEW, check_only=True)
        self.mocks["current_images"].assert_called_once()
        for name in ("build", "backup", "rollout", "run"):
            self.mocks[name].assert_not_called()

    def test_preflight_requires_backup_key_and_disk_space(self):
        for missing_key in (False, True):
            with self.subTest(missing_key=missing_key):
                if missing_key:
                    deploy.KEY.unlink()
                    self.disk.return_value.free = 7 * 1024**3
                else:
                    self.disk.return_value.free = 5 * 1024**3
                with self.assertRaisesRegex(
                    deploy.DeploymentError, "Backup key missing"
                ):
                    deploy.deploy(NEW, check_only=True)
                self.mocks["current_images"].assert_not_called()

    def test_already_deployed_requires_healthy_containers(self):
        self.mocks["git"].return_value = NEW
        self.mocks["run"].return_value = NEW
        deploy.deploy(NEW)
        self.mocks["wait_healthy"].assert_called_once_with(OLD_IMAGES)
        self.mocks["build"].assert_not_called()
        self.mocks["rollout"].assert_not_called()

    def test_already_deployed_unhealthy_is_not_reported_successful(self):
        self.mocks["git"].return_value = NEW
        self.mocks["run"].return_value = NEW
        self.mocks["wait_healthy"].side_effect = deploy.DeploymentError("unhealthy")
        with self.assertRaisesRegex(deploy.DeploymentError, "unhealthy"):
            deploy.deploy(NEW)

    def test_matching_checkout_with_mismatched_image_revision_is_rebuilt(self):
        self.mocks["git"].return_value = NEW
        self.mocks["run"].side_effect = lambda *args: (
            OLD if args[1:3] == ("image", "inspect") else ""
        )
        deploy.deploy(NEW)
        self.mocks["build"].assert_called_once()
        self.mocks["rollout"].assert_called_once_with(NEW, NEW, NEW_IMAGES, OLD_IMAGES)

    def test_success_records_previous_release_and_verified_target(self):
        deploy.deploy(NEW)
        (record_path,) = self.directory.glob("*/release.json")
        self.assertEqual(
            json.loads(record_path.read_text()),
            {"previous": OLD, "target": NEW, "rollback_images": OLD_IMAGES},
        )
        self.assertEqual((record_path.parent / "success").read_text(), NEW + "\n")
        self.mocks["backup"].assert_called_once_with(record_path.parent / "backup")
        self.mocks["rollout"].assert_called_once_with(NEW, OLD, NEW_IMAGES, OLD_IMAGES)


class RolloutTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.latest = self.stack.enter_context(patch.object(deploy, "require_latest"))
        self.clean = self.stack.enter_context(patch.object(deploy, "require_clean"))
        self.git = self.stack.enter_context(patch.object(deploy, "git"))
        self.start = self.stack.enter_context(patch.object(deploy, "start"))
        self.healthy = self.stack.enter_context(patch.object(deploy, "wait_healthy"))
        self.head = OLD

        def git(*args):
            if args[0] in ("merge", "reset"):
                self.head = args[-1]
            return self.head if args[0] == "rev-parse" else ""

        self.git.side_effect = git

    def test_health_failure_restores_and_verifies_old_images(self):
        self.healthy.side_effect = [deploy.DeploymentError("unhealthy"), None]
        with self.assertRaisesRegex(
            deploy.DeploymentError, "previous application release restored"
        ):
            deploy.rollout(NEW, OLD, NEW_IMAGES, OLD_IMAGES)
        self.assertEqual(self.head, OLD)
        self.assertEqual(
            self.start.call_args_list, [call(NEW_IMAGES), call(OLD_IMAGES)]
        )
        self.assertEqual(
            self.healthy.call_args_list, [call(NEW_IMAGES), call(OLD_IMAGES)]
        )

    def test_start_failure_also_rolls_back(self):
        self.start.side_effect = [deploy.DeploymentError("start failed"), None]
        with self.assertRaisesRegex(deploy.DeploymentError, "restored"):
            deploy.rollout(NEW, OLD, NEW_IMAGES, OLD_IMAGES)
        self.healthy.assert_called_once_with(OLD_IMAGES)

    def test_merge_failure_restores_old_images_and_reports_failure(self):
        real_git = self.git.side_effect

        def failing_merge(*args):
            if args[0] == "merge":
                raise deploy.DeploymentError("merge interrupted")
            return real_git(*args)

        self.git.side_effect = failing_merge
        with self.assertRaisesRegex(deploy.DeploymentError, "restored"):
            deploy.rollout(NEW, OLD, NEW_IMAGES, OLD_IMAGES)
        self.start.assert_called_once_with(OLD_IMAGES)
        self.healthy.assert_called_once_with(OLD_IMAGES)

    def test_rollback_failure_cannot_claim_release_was_restored(self):
        self.healthy.side_effect = [
            deploy.DeploymentError("new unhealthy"),
            deploy.DeploymentError("rollback unhealthy"),
        ]
        with self.assertRaisesRegex(deploy.DeploymentError, "rollback unhealthy"):
            deploy.rollout(NEW, OLD, NEW_IMAGES, OLD_IMAGES)

    def test_stale_head_after_build_never_starts_release(self):
        self.latest.side_effect = deploy.DeploymentError("main advanced")
        with self.assertRaisesRegex(deploy.DeploymentError, "main advanced"):
            deploy.rollout(NEW, OLD, NEW_IMAGES, OLD_IMAGES)
        self.git.assert_not_called()
        self.start.assert_not_called()

    def test_operator_checkout_change_before_cutover_is_preserved(self):
        self.head = "c" * 40
        with self.assertRaisesRegex(
            deploy.DeploymentError, "checkout changed during build"
        ):
            deploy.rollout(NEW, OLD, NEW_IMAGES, OLD_IMAGES)
        self.start.assert_not_called()
        self.assertNotIn(call("reset", "--hard", OLD), self.git.call_args_list)

    def test_operator_checkout_change_during_cutover_prevents_destructive_reset(self):
        def health(_images):
            self.head = "c" * 40
            raise deploy.DeploymentError("unhealthy")

        self.healthy.side_effect = health
        with self.assertRaisesRegex(deploy.DeploymentError, "Rollback refused"):
            deploy.rollout(NEW, OLD, NEW_IMAGES, OLD_IMAGES)
        self.assertNotIn(call("reset", "--hard", OLD), self.git.call_args_list)
        self.start.assert_called_once_with(NEW_IMAGES)


if __name__ == "__main__":
    unittest.main()

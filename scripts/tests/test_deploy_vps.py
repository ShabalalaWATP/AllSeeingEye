"""Deployment safety regressions using temporary storage and mocked processes."""

import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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


class GuardTests(unittest.TestCase):
    def test_invalid_revision_is_rejected_before_any_process(self):
        for sha in ("main", NEW + ";id", NEW.upper(), NEW + "\n", "-" + NEW):
            with self.subTest(sha=sha), patch.object(deploy, "git") as git:
                with self.assertRaises(deploy.DeploymentError):
                    deploy.require_latest(sha)
                git.assert_not_called()

    def test_outdated_requested_main_is_refused(self):
        with (
            patch.object(deploy, "git", side_effect=["", OLD]),
            self.assertRaisesRegex(deploy.DeploymentError, "no longer the head"),
        ):
            deploy.require_latest(NEW)

    def test_dirty_checkout_and_wrong_branch_are_refused(self):
        for values in ([" M changed.py"], ["", "feature/other"]):
            with (
                self.subTest(values=values),
                patch.object(deploy, "git", side_effect=values),
                self.assertRaises(deploy.DeploymentError),
            ):
                deploy.require_clean()

    def test_protected_paths_require_manual_rollout(self):
        paths = (
            "docker-compose.yml",
            "compose.yaml",
            "backend/alembic/versions/new.py",
            "backend/alembic.ini",
            "backend/src/ase/infrastructure/migrations.py",
            "backend/src/ase/cli.py",
            "scripts/deploy_vps.py",
            "scripts/deploy_ssh.py",
        )
        for path in paths:
            with (
                self.subTest(path=path),
                patch.object(
                    deploy, "git", side_effect=["", path, "different controller"]
                ),
                self.assertRaisesRegex(deploy.DeploymentError, "manual rollout"),
            ):
                deploy.require_compatible(OLD, NEW)

    def test_controller_upgrade_requires_exact_preinstalled_version(self):
        for name in ("deploy_vps.py", "deploy_ssh.py"):
            installed = Path(deploy.__file__).with_name(name).read_text().strip()
            with (
                self.subTest(name=name),
                patch.object(
                    deploy, "git", side_effect=["", f"scripts/{name}", installed]
                ),
            ):
                deploy.require_compatible(OLD, NEW)

    def test_application_change_is_compatible(self):
        with patch.object(
            deploy, "git", side_effect=["", "backend/src/ase/domain/event.py"]
        ):
            deploy.require_compatible(OLD, NEW)

    def test_non_fast_forward_is_refused_before_path_check(self):
        with patch.object(
            deploy, "git", side_effect=deploy.DeploymentError("not ancestor")
        ) as git:
            with self.assertRaises(deploy.DeploymentError):
                deploy.require_compatible(OLD, NEW)
            self.assertEqual(git.call_count, 1)

    def test_process_errors_do_not_expose_captured_output(self):
        error = subprocess.CalledProcessError(
            1, ["docker"], output="secret", stderr="secret"
        )
        with (
            patch.object(deploy.subprocess, "run", side_effect=error),
            self.assertRaises(deploy.DeploymentError) as caught,
        ):
            deploy.run("docker", "build")
        self.assertNotIn("secret", str(caught.exception))

    def test_process_arguments_are_passed_without_shell_evaluation(self):
        with patch.object(
            deploy.subprocess, "run", return_value=SimpleNamespace(stdout=" ok\n")
        ) as run:
            self.assertEqual(deploy.run("git", "show", "literal; argument"), "ok")
        self.assertEqual(run.call_args.args[0], ("git", "show", "literal; argument"))
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_invalid_utf8_process_output_becomes_safe_deployment_error(self):
        error = UnicodeDecodeError("utf-8", b"\xffsecret", 0, 1, "invalid byte")
        with (
            patch.object(deploy.subprocess, "run", side_effect=error),
            self.assertRaises(deploy.DeploymentError) as caught,
        ):
            deploy.run("curl", "--fail")
        self.assertEqual(str(caught.exception), "Operation failed: curl --fail")


class HealthTests(unittest.TestCase):
    def test_correct_images_and_healthy_services_reach_smoke_check(self):
        states = {
            "api": "sha256:new-api running healthy",
            "parser": "sha256:new-api running healthy",
            "web": "sha256:new-web running none",
        }
        with (
            patch.object(deploy, "compose", side_effect=lambda *args: args[-1]),
            patch.object(deploy, "run", side_effect=lambda *args: states[args[-1]]),
            patch.object(deploy, "smoke") as smoke,
        ):
            deploy.wait_healthy(NEW_IMAGES)
        smoke.assert_called_once()

    def test_frontend_asset_and_admin_auth_are_checked(self):
        with patch.object(
            deploy,
            "run",
            side_effect=[
                '{"status":"ok"}',
                '{"status":"ready"}',
                '<script src="/assets/app.js"></script>',
                "",
                "401",
            ],
        ) as run:
            deploy.smoke()
        self.assertEqual(
            run.call_args_list[-2].args[-1], deploy.SITE + "/assets/app.js"
        )
        self.assertEqual(
            run.call_args_list[-1].args[-1], deploy.SITE + "/api/admin/sources"
        )

    def test_invalid_health_response_is_refused(self):
        for body in ("not json", '{"status":"unavailable"}', "null", "[]", '"ok"'):
            with (
                self.subTest(body=body),
                patch.object(deploy, "run", return_value=body),
                self.assertRaises(deploy.DeploymentError),
            ):
                deploy.smoke()

    def test_missing_frontend_or_open_admin_endpoint_is_refused(self):
        prefix = ['{"status":"ok"}', '{"status":"ready"}']
        for tail in (
            ["<html></html>"],
            ['<script src="/assets/app.js"></script>', "", "200"],
        ):
            with (
                self.subTest(tail=tail),
                patch.object(deploy, "run", side_effect=prefix + tail),
                self.assertRaises(deploy.DeploymentError),
            ):
                deploy.smoke()

    def test_image_mismatch_cannot_pass_public_health_check(self):
        with (
            patch.object(deploy, "compose", return_value="container"),
            patch.object(deploy, "run", return_value="wrong running"),
            patch.object(deploy, "smoke") as smoke,
            patch.object(deploy.time, "sleep"),
        ):
            with self.assertRaisesRegex(
                deploy.DeploymentError, "Unexpected running image"
            ):
                deploy.wait_healthy(NEW_IMAGES)
            smoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()

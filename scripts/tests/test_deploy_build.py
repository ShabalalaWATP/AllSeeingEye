"""Regression checks for build-context permissions and isolated runtime probes."""

import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deploy_build
import deploy_vps

SHA = "b" * 40


def image_output(*args, **_kwargs):
    if args[:3] == ("docker", "image", "inspect"):
        return "sha256:api" if "ase-api:" in args[-1] else "sha256:web"
    return ""


class BuildTests(unittest.TestCase):
    def test_only_checkout_child_changes_mask(self):
        run = Mock(side_effect=image_output)
        images = deploy_build.build_images(SHA, Path("private/source"), run)
        self.assertEqual(
            images, {"api": "sha256:api", "parser": "sha256:api", "web": "sha256:web"}
        )
        self.assertEqual(run.call_args_list[0].kwargs, {"mask": 0o022})
        self.assertEqual(
            run.call_args_list[0].args[:4], ("git", "worktree", "add", "--detach")
        )
        for command in run.call_args_list[1:]:
            self.assertNotIn("mask", command.kwargs)

    def test_runtime_probes_keep_image_user_without_network_or_mounts(self):
        run = Mock(side_effect=image_output)
        deploy_build.build_images(SHA, Path("private/source"), run)
        probes = [
            item.args
            for item in run.call_args_list
            if item.args[:2] == ("docker", "run")
        ]
        self.assertEqual(len(probes), 2)
        for command in probes:
            self.assertIn("--read-only", command)
            self.assertEqual(command[command.index("--network") + 1], "none")
            for forbidden in (
                "--user",
                "-u",
                "--volume",
                "-v",
                "--mount",
                "--env-file",
                "--privileged",
            ):
                self.assertNotIn(forbidden, command)
        self.assertIn("sha256:api", probes[0])
        self.assertIn("ase.infrastructure.migrations", probes[0][-1])
        self.assertIn("ase.adapters.research_imports.service", probes[0][-1])
        self.assertIn("sha256:web", probes[1])
        self.assertIn("test -r /etc/caddy/Caddyfile", probes[1][-1])
        self.assertIn("test -r /srv/index.html", probes[1][-1])

    def test_failed_runtime_probe_cannot_return_deployable_images(self):
        for failed_image in ("sha256:api", "sha256:web"):

            def run(*args, failed_image=failed_image, **kwargs):
                if args[:2] == ("docker", "run") and failed_image in args:
                    raise deploy_vps.DeploymentError("runtime files unreadable")
                return image_output(*args, **kwargs)

            with (
                self.subTest(image=failed_image),
                self.assertRaisesRegex(
                    deploy_vps.DeploymentError, "runtime files unreadable"
                ),
            ):
                deploy_build.build_images(SHA, Path("private/source"), run)

    @unittest.skipUnless(
        os.name == "posix" and shutil.which("git"),
        "requires POSIX Git checkout permissions",
    )
    def test_real_checkout_is_readable_inside_private_release_without_changing_parent_mask(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            repository.mkdir()
            deploy_vps.run("git", "init", cwd=repository)
            source = repository / "package" / "module.py"
            source.parent.mkdir()
            source.write_text("VALUE = 1\n")
            deploy_vps.run("git", "add", ".", cwd=repository)
            deploy_vps.run(
                "git",
                "-c",
                "user.name=Deployment Test",
                "-c",
                "user.email=deploy@example.invalid",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                "Permission fixture",
                cwd=repository,
            )
            sha = deploy_vps.run("git", "rev-parse", "HEAD", cwd=repository)
            previous_mask = os.umask(0o077)
            try:
                release = Path(directory) / "release"
                release.mkdir()
                worktree = release / "source"

                def run(*args, **kwargs):
                    if args[0] == "git":
                        return deploy_vps.run(*args, cwd=repository, **kwargs)
                    return image_output(*args, **kwargs)

                deploy_build.build_images(sha, worktree, run)
                self.assertEqual(stat.S_IMODE(release.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE(worktree.stat().st_mode), 0o755)
                self.assertEqual(
                    stat.S_IMODE((worktree / "package").stat().st_mode), 0o755
                )
                self.assertEqual(
                    stat.S_IMODE((worktree / "package/module.py").stat().st_mode), 0o644
                )
                sentinel = release / "private-after-checkout"
                sentinel.write_text("private\n")
                self.assertEqual(stat.S_IMODE(sentinel.stat().st_mode), 0o600)
                self.assertEqual(os.umask(0o077), 0o077)
            finally:
                os.umask(previous_mask)


if __name__ == "__main__":
    unittest.main()

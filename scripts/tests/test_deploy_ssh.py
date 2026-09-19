"""The deployment SSH key must never accept arbitrary shell commands."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deploy_ssh


class ForcedCommandTests(unittest.TestCase):
    def test_only_exact_deploy_and_check_verbs_are_accepted(self):
        sha = "0123456789abcdef" * 2 + "01234567"
        self.assertEqual(deploy_ssh.parse_command(f"deploy {sha}"), (sha, False))
        self.assertEqual(deploy_ssh.parse_command(f"check {sha}"), (sha, True))

    def test_shell_syntax_and_malformed_revisions_are_rejected(self):
        sha = "a" * 40
        commands = (
            "",
            "bash",
            "deploy main",
            f"deploy {sha}; id",
            f"deploy {sha} && id",
            f"deploy $({sha})",
            f"deploy `{sha}`",
            f"deploy {sha}\nid",
            f"deploy {sha}\n",
            f"deploy {sha} ",
            f" deploy {sha}",
            f"deploy  {sha}",
            f"deploy\t{sha}",
            f"deploy {sha.upper()}",
            f"deploy {sha[:-1]}",
            f"deploy {sha}a",
            f"check {sha};id",
            f"scp -t {sha}",
            f"deploy -- {sha}",
            f"check {sha}\x00",
        )
        for command in commands:
            with self.subTest(command=command), self.assertRaises(ValueError):
                deploy_ssh.parse_command(command)


if __name__ == "__main__":
    unittest.main()

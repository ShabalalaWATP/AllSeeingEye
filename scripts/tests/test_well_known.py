"""The web image's robots.txt, security.txt and /.well-known routing.

scripts/check_web_image.py proves the built Caddy image serves these; this checks the
committed files and Caddy rule so a broken edit fails before an image is built.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "frontend" / "public"
CADDYFILE = ROOT / "infra" / "Caddyfile"


def fields(path: Path) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            name, _, value = line.partition(":")
            found.setdefault(name.strip().lower(), []).append(value.strip())
    return found


class RobotsTests(unittest.TestCase):
    def test_keeps_crawlers_out_of_the_api_and_administration(self) -> None:
        robots = fields(PUBLIC / "robots.txt")
        self.assertEqual(robots["user-agent"], ["*"])
        self.assertEqual(sorted(robots["disallow"]), ["/admin", "/api/"])
        self.assertEqual(robots["allow"], ["/enterprise", "/"])


class CaddyRoutingTests(unittest.TestCase):
    def test_well_known_paths_never_fall_back_to_the_shell(self) -> None:
        text = CADDYFILE.read_text(encoding="utf-8")
        block = re.search(r"@spa_route \{(.*?)\}", text, re.DOTALL)
        assert block is not None
        excluded = re.search(r"not path ([^\n]+)", block.group(1))
        assert excluded is not None
        self.assertIn("/.well-known/*", excluded.group(1).split())
        self.assertIn("/assets/*", excluded.group(1).split())


if __name__ == "__main__":
    unittest.main()

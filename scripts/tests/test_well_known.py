"""The web image's robots.txt, security.txt and /.well-known routing.

scripts/check_web_image.py proves the built Caddy image serves these; this checks the
committed files and Caddy rule so a broken edit fails before an image is built.
"""

import re
import unittest
from datetime import UTC, datetime, timedelta
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
        self.assertEqual(robots["allow"], ["/"])


class SecurityTxtTests(unittest.TestCase):
    """RFC 9116: Contact and Expires are required; Expires should be under a year."""

    def setUp(self) -> None:
        self.path = PUBLIC / ".well-known" / "security.txt"
        self.fields = fields(self.path)

    def test_required_fields_and_contact(self) -> None:
        self.assertEqual(
            self.fields["contact"],
            ["https://github.com/ShabalalaWATP/AllSeeingEye/security/advisories/new"],
        )
        self.assertEqual(self.fields["preferred-languages"], ["en"])
        for name in ("expires", "canonical"):
            self.assertEqual(len(self.fields[name]), 1, name)
        self.assertRegex(
            self.fields["canonical"][0], r"^https://[^/]+/\.well-known/security\.txt$"
        )

    def test_expiry_is_current_and_under_a_year_away(self) -> None:
        expires = datetime.fromisoformat(self.fields["expires"][0])
        self.assertIsNotNone(expires.tzinfo)
        now = datetime.now(UTC)
        self.assertGreater(expires, now, "security.txt has expired; renew Expires")
        self.assertLess(expires, now + timedelta(days=366))

    def test_plain_lf_text(self) -> None:
        raw = self.path.read_bytes()
        self.assertNotIn(b"\r", raw)
        raw.decode("ascii")


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

"""CI's PostgreSQL service must test the same PostGIS image that production runs."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = re.compile(r"image:\s*(postgis/postgis:\S+)")


def pinned(path: Path) -> list[str]:
    return PIN.findall(path.read_text(encoding="utf-8"))


class DatabaseImagePinTest(unittest.TestCase):
    def test_ci_service_matches_compose(self) -> None:
        compose = pinned(ROOT / "docker-compose.yml")
        ci = pinned(ROOT / ".github" / "workflows" / "ci.yml")
        self.assertEqual(len(compose), 1, "docker-compose.yml should pin one PostGIS image")
        self.assertTrue(ci, "ci.yml should run a PostGIS service")
        self.assertEqual(set(ci), set(compose))

    def test_image_is_pinned_by_digest(self) -> None:
        (image,) = pinned(ROOT / "docker-compose.yml")
        self.assertRegex(image, r"@sha256:[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()

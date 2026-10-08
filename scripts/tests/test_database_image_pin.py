"""CI's PostgreSQL service must test the same PostGIS base that production builds on."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "infra" / "postgis" / "Dockerfile"
SERVICE = re.compile(r"image:\s*(postgis/postgis:\S+)")
BASE = re.compile(r"^FROM\s+(postgis/postgis:\S+)\s*$", re.MULTILINE)


class DatabaseImagePinTest(unittest.TestCase):
    def test_compose_builds_the_database_image(self) -> None:
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        db = compose.split("\n  db:\n", 1)[1].split("\n  api:\n", 1)[0]
        self.assertIn("build: ./infra/postgis", db)
        self.assertNotIn("image:", db)

    def test_ci_service_matches_production_base(self) -> None:
        (base,) = BASE.findall(DOCKERFILE.read_text(encoding="utf-8"))
        ci = SERVICE.findall((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
        self.assertTrue(ci, "ci.yml should run a PostGIS service")
        self.assertEqual(set(ci), {base})

    def test_base_is_pinned_by_digest(self) -> None:
        (base,) = BASE.findall(DOCKERFILE.read_text(encoding="utf-8"))
        self.assertRegex(base, r"@sha256:[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()

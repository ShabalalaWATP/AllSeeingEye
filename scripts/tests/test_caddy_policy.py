"""Keep the production Caddy policy in step with what the web client loads.

The development server sends no Content-Security-Policy, so a camera host that the
client admits but Caddy omits only fails on the live site. These checks read the same
host list the client uses (frontend/src/lib/api/cameraMediaHosts.json).
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CADDYFILE = ROOT / "infra" / "Caddyfile"
CAMERA_HOSTS = ROOT / "frontend" / "src" / "lib" / "api" / "cameraMediaHosts.json"


def spa_policy() -> dict[str, list[str]]:
    """The directives of the policy Caddy sends with the single-page application."""
    text = CADDYFILE.read_text(encoding="utf-8")
    policies = re.findall(r'Content-Security-Policy "([^"]+)"', text)
    if len(policies) != 1:
        raise AssertionError(
            f"Expected one SPA policy in the Caddyfile, found {len(policies)}."
        )
    directives: dict[str, list[str]] = {}
    for part in policies[0].split(";"):
        tokens = part.split()
        if tokens:
            directives[tokens[0]] = tokens[1:]
    return directives


def https_hosts(sources: list[str]) -> set[str]:
    """Hostnames of https:// sources; a path-scoped source still names its host."""
    return {
        source.removeprefix("https://").split("/", 1)[0]
        for source in sources
        if source.startswith("https://")
    }


class CameraPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = spa_policy()
        hosts = json.loads(CAMERA_HOSTS.read_text(encoding="utf-8"))
        self.media = set(hosts["media"])
        self.frames = set(hosts["frames"])

    def assert_admits(self, directive: str, hosts: set[str]) -> None:
        missing = sorted(hosts - https_hosts(self.policy.get(directive, [])))
        self.assertEqual(missing, [], f"{directive} omits hosts the client admits")

    def test_every_camera_image_host_is_an_image_source(self) -> None:
        self.assert_admits("img-src", self.media)

    def test_every_camera_stream_host_can_play(self) -> None:
        # isCameraStreamUrl admits any media host; native video needs media-src and
        # hls.js fetches playlists and segments, which needs connect-src.
        self.assert_admits("media-src", self.media)
        self.assert_admits("connect-src", self.media)

    def test_every_embedded_player_host_is_a_frame_source(self) -> None:
        self.assert_admits("frame-src", self.frames)

    def test_policy_stays_locked_down(self) -> None:
        self.assertEqual(self.policy["default-src"], ["'self'"])
        self.assertEqual(self.policy["script-src"], ["'self'"])
        self.assertEqual(self.policy["object-src"], ["'none'"])
        self.assertEqual(self.policy["frame-ancestors"], ["'none'"])
        for directive, sources in self.policy.items():
            self.assertNotIn(
                "http:", " ".join(sources).replace("https:", ""), directive
            )
            self.assertNotIn("*", " ".join(sources), directive)


class StaticCachingTests(unittest.TestCase):
    def test_only_content_hashed_assets_are_immutable(self) -> None:
        text = CADDYFILE.read_text(encoding="utf-8")
        pattern = re.search(r"@hashed_asset path_regexp (\S+)", text)
        assert pattern is not None
        hashed = re.compile(pattern.group(1))
        self.assertIsNotNone(hashed.match("/assets/index-Bwx2Xxg9.js"))
        self.assertIsNotNone(
            hashed.match("/assets/inter-latin-wght-normal-Dx4kXJAl.woff2")
        )
        # Rolldown hashes may themselves contain a hyphen.
        self.assertIsNotNone(hashed.match("/assets/StatusPill-s7-CsJq8.js"))
        # Fixed-name files would pin a stale MapLibre worker after an upgrade.
        self.assertIsNone(hashed.match("/assets/maplibre-gl-worker.mjs"))
        self.assertIsNone(hashed.match("/index.html"))
        self.assertIsNone(hashed.match("/assets/nested/index-Bwx2Xxg9.js"))


if __name__ == "__main__":
    unittest.main()

"""Crawler controls keep application URLs out of search without blocking product rendering."""

import fnmatch
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PublicPagePolicyTests(unittest.TestCase):
    def test_caddy_noindex_covers_app_routes_but_not_the_product_or_its_assets(self):
        text = (ROOT / "infra/Caddyfile").read_text(encoding="utf-8")
        matcher = re.search(r"@app_page \{([^}]+)\}", text)
        self.assertIsNotNone(matcher)
        assert matcher is not None
        exceptions = re.findall(r"not path ([^\n]+)", matcher.group(1))
        paths = " ".join(exceptions).split()

        def noindex(path):
            return not any(fnmatch.fnmatchcase(path, item) for item in paths)

        for route in (
            "/",
            "/index.html",
            "/login",
            "/research",
            "/reports/example",
            "/admin/users",
            "/privacy",
            "/privacy/requests",
            "/attributions",
        ):
            self.assertTrue(noindex(route), route)
        for route in (
            "/enterprise",
            "/enterprise/",
            "/assets/index-12345678.js",
            "/brand/eye-512.png",
            "/robots.txt",
        ):
            self.assertFalse(noindex(route), route)
        self.assertIn('header @app_page X-Robots-Tag "noindex, follow"', text)

    def test_shared_html_does_not_prevent_rendering_of_the_opt_in_product_page(self):
        html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r'<meta[^>]+name="robots"[^>]+noindex')
        robots = (ROOT / "frontend/public/robots.txt").read_text(encoding="utf-8")
        self.assertIn("Allow: /enterprise", robots)
        self.assertIn("Disallow: /api/", robots)


if __name__ == "__main__":
    unittest.main()

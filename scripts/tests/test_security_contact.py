"""Generated RFC 9116 responses, disabled state and expiry monitoring."""

import sys
import unittest
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_security_contact import expiry_warning, problems

BASE = "https://example.test"
CONTACT = "mailto:security@example.test"
CANONICAL = BASE + "/.well-known/security.txt"


class SecurityContactTests(unittest.TestCase):
    def response(self, status=200):
        headers = Message()
        headers["Content-Type"] = "text/plain; charset=utf-8"
        for key in (
            "Content-Security-Policy",
            "Strict-Transport-Security",
            "Permissions-Policy",
            "Referrer-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
        ):
            headers[key] = "present"
        expiry = (datetime.now(UTC) + timedelta(days=100)).isoformat()
        body = (
            f"Contact: {CONTACT}\nExpires: {expiry}\nPreferred-Languages: en\n"
            f"Canonical: {CANONICAL}\n"
            "Policy: https://github.com/ShabalalaWATP/AllSeeingEye/security/policy\n"
        ).encode()
        return status, headers, body

    def test_valid_enabled_response_and_disabled_not_found(self):
        with patch("check_security_contact.fetch", return_value=self.response()):
            self.assertEqual(problems(BASE, CONTACT, CANONICAL), [])
            self.assertTrue(problems(BASE, None, None))
        with patch("check_security_contact.fetch", return_value=self.response(404)):
            self.assertEqual(problems(BASE, None, None), [])
            self.assertTrue(problems(BASE, CONTACT, CANONICAL))

    def test_spa_fallback_wrong_host_contact_headers_and_expiry_fail(self):
        status, headers, body = self.response()
        for invalid in (
            b"<html>app shell</html>",
            body.replace(CONTACT.encode(), b"mailto:wrong@example.test"),
            body.replace(
                CANONICAL.encode(), b"https://wrong.example.test/security.txt"
            ),
            body + b"Contact: mailto:duplicate@example.test\n",
            body.replace(b"Expires:", b"Missing:"),
            body.replace(b"Expires:", b"Expires: invalid"),
            body.replace(b"Preferred-Languages: en", b"malformed"),
            body.rstrip(),
        ):
            with (
                self.subTest(invalid=invalid),
                patch(
                    "check_security_contact.fetch",
                    return_value=(status, headers, invalid),
                ),
            ):
                self.assertTrue(problems(BASE, CONTACT, CANONICAL))
        with patch(
            "check_security_contact.fetch", return_value=(status, Message(), body)
        ):
            self.assertTrue(problems(BASE, CONTACT, CANONICAL))

    def test_expiry_boundaries_warn_without_blocking_unrelated_ci(self):
        now = datetime(2026, 10, 16, tzinfo=UTC)
        for days in (-1, 0, 30):
            self.assertIsNotNone(
                expiry_warning((now + timedelta(days=days)).isoformat(), now)
            )
        self.assertIsNone(expiry_warning((now + timedelta(days=31)).isoformat(), now))
        for value in ("invalid", "2027-01-01T00:00:00", "2030-01-01T00:00:00Z"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                expiry_warning(value, now)


if __name__ == "__main__":
    unittest.main()

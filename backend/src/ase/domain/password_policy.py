"""Password policy: length and a deny-list, not composition rules."""

from __future__ import annotations

import string
from functools import cache
from importlib import resources

from ase.domain.errors import WeakPassword

MIN_LENGTH = 12
MAX_LENGTH = 128
MIN_CORE_LENGTH = 4
STRIP_CHARS = string.digits + string.punctuation + string.whitespace


@cache
def common_passwords() -> frozenset[str]:
    """The 10,000 most common passwords, lower-cased, loaded once."""
    text = resources.files("ase.domain").joinpath("common_passwords.txt").read_text("utf-8")
    return frozenset(line.strip().lower() for line in text.splitlines() if line.strip())


def _core(password: str) -> str:
    """Strip the digits and punctuation people bolt onto a common word ("password1234")."""
    return password.strip(STRIP_CHARS)


def validate_password(password: str, email: str) -> None:
    """Raise WeakPassword with a specific reason when the password is not acceptable."""
    if len(password) < MIN_LENGTH:
        raise WeakPassword(f"Use at least {MIN_LENGTH} characters.")
    if len(password) > MAX_LENGTH:
        raise WeakPassword(f"Use at most {MAX_LENGTH} characters.")
    lowered = password.lower()
    core = _core(lowered)
    common = common_passwords()
    if lowered in common or (len(core) >= MIN_CORE_LENGTH and core in common):
        raise WeakPassword("This password is too common.")
    email_lower = email.strip().lower()
    local_part = email_lower.split("@", 1)[0]
    if lowered in {email_lower, local_part}:
        raise WeakPassword("The password must not be your email address.")

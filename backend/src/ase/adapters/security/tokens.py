"""Opaque secrets for refresh and password tokens; only SHA-256 digests are stored."""

from __future__ import annotations

import hashlib
import secrets


class SecretsTokenGenerator:
    def __init__(self, nbytes: int = 48) -> None:
        self._nbytes = nbytes

    def new_secret(self) -> str:
        return secrets.token_urlsafe(self._nbytes)

    def hash(self, secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

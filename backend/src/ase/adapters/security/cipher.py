"""Fernet encryption for secrets at rest, keyed from ASE_ENCRYPTION_KEY.

Any string of at least 32 characters works as the setting: it is hashed to the 32-byte
key Fernet needs, so operators can paste any long random value rather than a base64 one.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

MIN_KEY_CHARS = 32


class CipherUnavailable(Exception):
    """No encryption key is configured, so secrets cannot be stored or read."""


class FernetCipher:
    def __init__(self, secret: str | None) -> None:
        self._fernet: Fernet | None = None
        if secret is not None and len(secret.strip()) >= MIN_KEY_CHARS:
            digest = hashlib.sha256(secret.strip().encode("utf-8")).digest()
            self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    @property
    def available(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        if self._fernet is None:
            raise CipherUnavailable()
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        if self._fernet is None:
            raise CipherUnavailable()
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            msg = "The stored secret cannot be read with the current encryption key."
            raise CipherUnavailable(msg) from exc

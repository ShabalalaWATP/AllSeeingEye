"""RFC 6238 through PyOTP, with encrypted secrets and a single adjacent time step."""

from datetime import datetime, timedelta

import pyotp

from ase.adapters.security.cipher import CipherUnavailable
from ase.application.ports.llm import SecretCipher
from ase.domain.errors import EncryptionUnavailable
from ase.domain.totp import TotpEnrolment


class EncryptedTotpProvider:
    def __init__(self, cipher: SecretCipher) -> None:
        self._cipher = cipher

    @property
    def available(self) -> bool:
        return self._cipher.available

    def enrol(self, email: str) -> TotpEnrolment:
        secret = pyotp.random_base32()
        try:
            encrypted = self._cipher.encrypt(secret)
        except CipherUnavailable as exc:
            raise EncryptionUnavailable(
                "Configure ASE_ENCRYPTION_KEY before enabling TOTP."
            ) from exc
        uri = pyotp.TOTP(secret).provisioning_uri(email, issuer_name="The All Seeing Eye")
        return TotpEnrolment(secret, uri, encrypted)

    def verify(self, encrypted: str, code: str, now: datetime) -> int | None:
        if len(code) != 6 or not code.isascii() or not code.isdecimal():
            return None
        try:
            secret = self._cipher.decrypt(encrypted)
        except CipherUnavailable as exc:
            raise EncryptionUnavailable("The TOTP encryption key is unavailable.") from exc
        totp = pyotp.TOTP(secret)
        # Verify with the library's constant-time comparison. Return the matched step
        # so the repository can consume it atomically, including adjacent-step codes.
        for offset in (0, -1, 1):
            at = now + timedelta(seconds=offset * totp.interval)
            if totp.verify(code, for_time=at):
                return totp.timecode(at)
        return None

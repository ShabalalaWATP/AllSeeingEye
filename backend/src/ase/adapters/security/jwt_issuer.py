"""Short-lived JWT access tokens. Expiry is checked against the application clock."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt

from ase.application.dto import AccessClaims, IssuedAccessToken
from ase.application.ports import Clock
from ase.domain.errors import Unauthenticated
from ase.domain.users import Role, User

ALGORITHM = "HS256"


class JwtAccessTokenIssuer:
    def __init__(self, secret: str, ttl: timedelta, clock: Clock) -> None:
        self._secret = secret
        self._ttl = ttl
        self._clock = clock

    def issue(self, user: User, family_id: UUID) -> IssuedAccessToken:
        now = self._clock.now()
        payload = {
            "sub": str(user.id),
            "role": user.role.value,
            "typ": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + self._ttl).timestamp()),
            "jti": uuid4().hex,
            "sid": str(family_id),
            "sv": user.security_version,
        }
        token = jwt.encode(payload, self._secret, algorithm=ALGORITHM)
        return IssuedAccessToken(token=token, expires_in=int(self._ttl.total_seconds()))

    def verify(self, token: str) -> AccessClaims:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._secret,
                algorithms=[ALGORITHM],
                options={
                    "require": ["sub", "exp", "iat", "jti", "typ", "sid", "sv"],
                    "verify_exp": False,
                    "verify_iat": False,
                },
            )
        except jwt.PyJWTError as exc:
            raise Unauthenticated() from exc
        if payload.get("typ") != "access":
            raise Unauthenticated()
        try:
            if type(payload["sv"]) is not int or payload["sv"] < 0:
                raise ValueError("Invalid security version")
            expires = int(payload["exp"])
            claims = AccessClaims(
                user_id=UUID(str(payload["sub"])),
                role=Role(str(payload.get("role"))),
                jti=str(payload["jti"]),
                expires_at=datetime.fromtimestamp(expires, tz=UTC),
                family_id=UUID(str(payload["sid"])),
                security_version=payload["sv"],
            )
        except (TypeError, ValueError, OverflowError, OSError) as exc:
            raise Unauthenticated() from exc
        if expires <= int(self._clock.now().timestamp()):
            raise Unauthenticated("The session has expired.")
        return claims

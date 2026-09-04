"""Session cookies: the refresh token is HttpOnly; the CSRF token is readable by the SPA."""

from __future__ import annotations

from fastapi import Response

from ase.application.dto import AuthSession
from ase.infrastructure.settings import Settings

REFRESH_COOKIE = "ase_refresh"
CSRF_COOKIE = "ase_csrf"
REFRESH_PATH = "/api/auth"
CSRF_HEADER = "x-csrf-token"


def set_session_cookies(response: Response, session: AuthSession, settings: Settings) -> None:
    max_age = settings.refresh_token_days * 86_400
    secure = bool(settings.cookie_secure)
    response.set_cookie(
        REFRESH_COOKIE,
        session.refresh_secret,
        max_age=max_age,
        path=REFRESH_PATH,
        secure=secure,
        httponly=True,
        samesite="strict",
    )
    response.set_cookie(
        CSRF_COOKIE,
        session.csrf_token,
        max_age=max_age,
        path="/",
        secure=secure,
        httponly=False,
        samesite="strict",
    )


def clear_session_cookies(response: Response, settings: Settings) -> None:
    secure = bool(settings.cookie_secure)
    response.delete_cookie(
        REFRESH_COOKIE, path=REFRESH_PATH, secure=secure, httponly=True, samesite="strict"
    )
    response.delete_cookie(CSRF_COOKIE, path="/", secure=secure, httponly=False, samesite="strict")

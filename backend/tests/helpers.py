"""Test doubles and helpers shared by the suite."""

from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from httpx import AsyncClient, Response

from ase.container import Container
from ase.domain.tokens import TokenPurpose
from ase.domain.users import Role, User

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Orbital-Watchtower-2026"
USER_EMAIL = "user@example.com"
USER_PASSWORD = "Glasgow-Rain-Falls-42"
CSRF_COOKIE = "ase_csrf"
REFRESH_COOKIE = "ase_refresh"


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta


class RecordingEmailSender:
    def __init__(self, delivered: bool) -> None:
        self.delivered = delivered
        self.sent: list[tuple[str, TokenPurpose, str]] = []

    async def send_link(self, to_email: str, purpose: TokenPurpose, link: str) -> bool:
        self.sent.append((to_email, purpose, link))
        return self.delivered


async def create_user(
    container: Container,
    *,
    email: str,
    password: str | None,
    role: Role = Role.USER,
    is_active: bool = True,
) -> User:
    async with container.session_factory() as session:
        repos = container.repositories(session)
        user = User(
            id=uuid4(),
            email=email,
            display_name=email.partition("@")[0].title(),
            role=role,
            is_active=is_active,
            password_hash=container.hasher.hash(password) if password else None,
            failed_login_count=0,
            last_failed_at=None,
            locked_until=None,
            created_at=container.clock.now(),
            last_login_at=None,
        )
        await repos.users.add(user)
        await repos.uow.commit()
        return user


async def login(client: AsyncClient, email: str, password: str) -> Response:
    return await client.post("/api/auth/login", json={"email": email, "password": password})


async def login_token(client: AsyncClient, email: str, password: str) -> str:
    response = await login(client, email, password)
    assert response.status_code == 200, response.text
    token: str = response.json()["access_token"]
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def csrf_headers(client: AsyncClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get(CSRF_COOKIE) or ""}


def override_cookie(client: AsyncClient, name: str, value: str, path: str = "/") -> None:
    """Replace a cookie in the jar. Domain-less cookies match any host, unlike "test"."""
    client.cookies.delete(name)
    client.cookies.set(name, value, path=path)


def restore_session(client: AsyncClient, refresh: str, csrf: str) -> dict[str, str]:
    override_cookie(client, REFRESH_COOKIE, refresh, path="/api/auth")
    override_cookie(client, CSRF_COOKIE, csrf)
    return {"X-CSRF-Token": csrf}


def token_from_link(link: str) -> str:
    values = parse_qs(urlparse(link).query).get("token")
    assert values, link
    return values[0]


def set_cookie_headers(response: Response) -> list[str]:
    return response.headers.get_list("set-cookie")

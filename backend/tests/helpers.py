"""Test doubles and helpers shared by the suite."""

from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4
from weakref import WeakKeyDictionary

import pyotp
from httpx import AsyncClient, Response

from ase.adapters.persistence.totp import SqlTotpRepository
from ase.container import Container
from ase.domain.tokens import TokenPurpose
from ase.domain.users import Role, User

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Orbital-Watchtower-2026"
USER_EMAIL = "user@example.com"
USER_PASSWORD = "Glasgow-Rain-Falls-42"
CSRF_COOKIE = "ase_csrf"
REFRESH_COOKIE = "ase_refresh"
_CLIENT_CONTAINERS: WeakKeyDictionary[AsyncClient, Container] = WeakKeyDictionary()


def register_client(client: AsyncClient, container: Container) -> None:
    """Bind synthetic clock and factors to a test client, never to production authentication."""
    _CLIENT_CONTAINERS[client] = container


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
        self.codes: list[tuple[str, str]] = []

    @property
    def available(self) -> bool:
        return self.delivered

    async def send_code(self, to_email: str, code: str) -> bool:
        self.codes.append((to_email, code))
        return self.delivered

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


async def password_login(client: AsyncClient, email: str, password: str) -> Response:
    """Only the password stage, for tests inspecting pending challenges and missing factors."""
    return await client.post("/api/auth/login", json={"email": email, "password": password})


async def login(client: AsyncClient, email: str, password: str) -> Response:
    """Complete real MFA APIs for authenticated fixtures, preserving failed password responses."""
    response = await password_login(client, email, password)
    if response.status_code != 200 or not response.json().get("mfa_required"):
        return response
    container = _CLIENT_CONTAINERS.get(client)
    if container is None:
        return response
    pending = response.json()
    challenge = pending["challenge_token"]
    if pending["enrollment_required"]:
        enrolment = await client.post(
            "/api/auth/mfa/enrol-app", json={"challenge_token": challenge}
        )
        assert enrolment.status_code == 200, enrolment.text
        secret = enrolment.json()["secret"]
    else:
        async with container.session_factory() as session:
            user = await container.repositories(session).users.get_by_email(email.strip().lower())
            assert user is not None
            state = await SqlTotpRepository(session).get(user.id)
        if state is None or state.secret_encrypted is None:
            # Email-only fixture users still exercise delivery and challenge verification.
            sender = container.email_sender
            assert isinstance(sender, RecordingEmailSender)
            if not pending["email_sent"]:
                sent = await client.post("/api/auth/mfa/email", json={"challenge_token": challenge})
                assert sent.status_code == 200, sent.text
            assert sender.codes and sender.codes[-1][0] == email.strip().lower()
            return await client.post(
                "/api/auth/mfa/verify",
                json={"challenge_token": challenge, "method": "email", "code": sender.codes[-1][1]},
            )
        secret = container.cipher.decrypt(state.secret_encrypted)
        clock = container.clock
        assert isinstance(clock, FakeClock)
        step = pyotp.TOTP(secret).timecode(clock.now())
        if state.last_step is not None and step <= state.last_step:
            clock.advance(timedelta(seconds=(state.last_step - step + 1) * 30))
    return await client.post(
        "/api/auth/mfa/verify",
        json={
            "challenge_token": challenge,
            "method": "authenticator",
            "code": pyotp.TOTP(secret).at(container.clock.now()),
        },
    )


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

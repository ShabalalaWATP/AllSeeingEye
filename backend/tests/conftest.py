"""Fixtures: a fresh in-memory database and app per test, a fake clock and a recording mailer."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from ase.adapters.persistence.base import Base
from ase.container import Container
from ase.domain.users import Role, User
from ase.infrastructure.settings import Environment, Settings
from ase.main import create_app
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    RecordingEmailSender,
    create_user,
)

START = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(START)


@pytest.fixture
def email_sender() -> RecordingEmailSender:
    return RecordingEmailSender(delivered=False)


@pytest.fixture
def settings() -> Settings:
    # CI runs the same suite against PostgreSQL by setting ASE_TEST_DATABASE_URL.
    return Settings(
        _env_file=None,
        env=Environment.TEST,
        database_url=os.environ.get("ASE_TEST_DATABASE_URL", "sqlite+aiosqlite://"),
        jwt_secret=SecretStr("t" * 40),
        encryption_key=SecretStr("e" * 40),
        public_base_url="http://app.test",
        cookie_secure=False,
    )


@pytest.fixture
async def app(
    settings: Settings, clock: FakeClock, email_sender: RecordingEmailSender
) -> AsyncIterator[FastAPI]:
    application = create_app(settings, clock=clock, email_sender=email_sender)
    container: Container = application.state.container
    async with container.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield application
    async with container.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await container.dispose()


@pytest.fixture
def container(app: FastAPI) -> Container:
    result: Container = app.state.container
    return result


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def admin(container: Container) -> User:
    return await create_user(container, email=ADMIN_EMAIL, password=ADMIN_PASSWORD, role=Role.ADMIN)


@pytest.fixture
async def user(container: Container) -> User:
    return await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)

"""Fixtures: a fresh in-memory database and app per test, a fake clock and a recording mailer.

The app is built without the live feed catalogue; tests that need the real connectors
carry the ``feed_catalogue`` marker. In-memory and not-yet-created SQLite databases start
empty, so their schema is created in one transaction without existence checks and is
discarded with the engine or tmp_path; shared databases such as CI's PostgreSQL are still
dropped and recreated. Test SQLite files skip fsync, which changes no locking behaviour.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from ase.app_factory import create_app
from ase.application.ports.feeds import FeedConnector
from ase.container import Container
from ase.domain.users import Role, User
from ase.infrastructure.settings import Environment, Settings
from helpers import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    FakeClock,
    RecordingEmailSender,
    create_user,
    register_client,
)
from pytest_support import (
    DurationRecorder,
    apply_markers,
    create_schema,
    disposable_database,
    drop_schema,
    refuse_shared_databases_in_parallel,
    skip_sqlite_fsync,
)

pytest_plugins = ["postgres_isolation"]

START = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--isolated-postgres",
        action="store_true",
        help="Create one disposable PostgreSQL database per worker from ASE_TEST_DATABASE_URL.",
    )
    parser.addoption("--record-nodeids", metavar="PATH", help="Write selected test node IDs.")
    parser.addoption(
        "--record-durations",
        metavar="PATH",
        help="Merge per-file test durations into this JSON file for balanced CI shards.",
    )


def pytest_configure(config: pytest.Config) -> None:
    refuse_shared_databases_in_parallel(config)
    target = config.getoption("--record-durations")
    # Under pytest-xdist the controller receives every worker's reports.
    if target and not hasattr(config, "workerinput"):
        config.pluginmanager.register(DurationRecorder(Path(target)), "ase-durations")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    apply_markers(items)


def pytest_collection_finish(session: pytest.Session) -> None:
    target = session.config.getoption("--record-nodeids")
    if target and not hasattr(session.config, "workerinput"):
        Path(target).write_text(
            "".join(f"{item.nodeid}\n" for item in session.items), encoding="utf-8"
        )


def pytest_xdist_node_collection_finished(node, ids: list[str]) -> None:
    target = node.config.getoption("--record-nodeids")
    if target:
        Path(target).write_text("".join(f"{nodeid}\n" for nodeid in ids), encoding="utf-8")


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
def feed_connectors(request: pytest.FixtureRequest) -> Sequence[FeedConnector] | None:
    """No feed catalogue unless marked ``feed_catalogue``; ``None`` builds the real one."""
    return None if request.node.get_closest_marker("feed_catalogue") else ()


@pytest.fixture
async def app(
    settings: Settings,
    clock: FakeClock,
    email_sender: RecordingEmailSender,
    feed_connectors: Sequence[FeedConnector] | None,
) -> AsyncIterator[FastAPI]:
    application = create_app(
        settings, clock=clock, email_sender=email_sender, connectors=feed_connectors
    )
    container: Container = application.state.container
    fresh = disposable_database(settings.database_url)
    skip_sqlite_fsync(container.engine)
    await create_schema(container.engine, fresh=fresh)
    yield application
    if not fresh:
        await drop_schema(container.engine)
    await container.dispose()


@pytest.fixture
def container(app: FastAPI) -> Container:
    result: Container = app.state.container
    return result


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        register_client(client, app.state.container)
        yield client


@pytest.fixture
async def admin(container: Container) -> User:
    return await create_user(container, email=ADMIN_EMAIL, password=ADMIN_PASSWORD, role=Role.ADMIN)


@pytest.fixture
async def user(container: Container) -> User:
    return await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)

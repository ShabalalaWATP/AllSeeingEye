"""Explicit template optimisation for the ordinary isolated PostgreSQL app fixture."""

import asyncio
import os
from collections import Counter
from collections.abc import Iterator

import pytest
from sqlalchemy.engine import make_url

from postgres_template_fixtures import template_fixture
from postgres_template_guard import ordinary_app, schema_fingerprint
from postgres_template_store import TemplateDatabase, TemplateWorker

SCHEMA = pytest.StashKey[str | None]()
COUNTS = pytest.StashKey[Counter[str]]()


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--template-postgres") and not config.getoption("--isolated-postgres"):
        raise pytest.UsageError("--template-postgres requires --isolated-postgres")
    if config.getoption("--template-postgres"):
        # SQLAlchemy allows query parameters to override authority/database components.
        # Check before the existing isolation fixture executes any service DDL.
        parsed = make_url(os.environ.get("ASE_TEST_DATABASE_URL", "sqlite://"))
        if (
            parsed.get_backend_name() != "postgresql"
            or parsed.host not in {"localhost", "127.0.0.1", "::1"}
            or parsed.query
        ):
            raise pytest.UsageError(
                "Templates require a local PostgreSQL URL without query options"
            )
    config.stash[SCHEMA] = schema_fingerprint() if config.getoption("--template-postgres") else None
    config.stash[COUNTS] = Counter()


@pytest.fixture(scope="session")
@template_fixture
def template_worker(
    request: pytest.FixtureRequest, isolated_postgres_database: str | None
) -> Iterator[TemplateWorker]:
    if isolated_postgres_database is None:
        raise pytest.UsageError("A template requires the isolated PostgreSQL worker fixture")
    worker = TemplateWorker(isolated_postgres_database, request.config.stash[SCHEMA])
    try:
        yield worker
    finally:
        asyncio.run(worker.close())


@pytest.fixture(autouse=True)
@template_fixture
def template_database(request: pytest.FixtureRequest) -> Iterator[TemplateDatabase | None]:
    """Run before settings/app and restore the worker URL after all app finalisers.

    Autouse also establishes the URL before independent function-scoped consumers;
    default settings/app depend on this fixture explicitly to enforce its lifetime.
    All other fixture graphs keep their original database selection.
    """
    if not request.config.getoption("--template-postgres"):
        yield None
        return
    counts = request.config.stash[COUNTS]
    if not ordinary_app(request.node):
        counts["ineligible"] += 1
        yield None
        return
    worker = request.getfixturevalue("template_worker")
    database = asyncio.run(worker.acquire())
    if database is None:
        counts["fallback"] += 1
        yield None
        return
    counts["cloned"] += 1
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("ASE_TEST_DATABASE_URL", database.url)
            yield database
    finally:
        asyncio.run(worker.release(database))


def pytest_sessionfinish(session: pytest.Session) -> None:
    if hasattr(session.config, "workeroutput"):
        session.config.workeroutput["template_counts"] = dict(session.config.stash[COUNTS])


def pytest_testnodedown(node, error) -> None:
    node.config.stash[COUNTS].update(node.workeroutput.get("template_counts", {}))


def pytest_terminal_summary(terminalreporter, config: pytest.Config) -> None:
    if config.getoption("--template-postgres"):
        counts = config.stash[COUNTS]
        terminalreporter.write_line(
            "PostgreSQL templates: "
            f"{counts['cloned']} cloned, {counts['fallback']} schema fallback, "
            f"{counts['ineligible']} ineligible fixture/lane cases"
        )

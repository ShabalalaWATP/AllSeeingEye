"""Explicitly opted-in, disposable PostgreSQL databases for pytest-xdist workers."""

import asyncio
import os
import re
from collections.abc import Iterator
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy.engine import make_url


def worker_database_url(service_url: str, worker: str, token: str) -> str:
    """Generate an identifier from trusted worker metadata, never from user SQL."""
    url = make_url(service_url)
    if url.get_backend_name() != "postgresql":
        raise pytest.UsageError("--isolated-postgres requires a PostgreSQL test service")
    if url.host not in {"127.0.0.1", "localhost", "::1"}:
        raise pytest.UsageError("--isolated-postgres requires a local disposable service")
    if not re.fullmatch(r"(?:gw[0-9]+|master)", worker) or not re.fullmatch(r"[a-f0-9]{32}", token):
        raise pytest.UsageError("Invalid isolated PostgreSQL worker identity")
    return url.set(database=f"ase_test_{token}_{worker}").render_as_string(hide_password=False)


async def database_command(service_url: str, database_url: str, *, create: bool) -> None:
    service = make_url(service_url).set(drivername="postgresql")
    database = make_url(database_url).database
    # Revalidate before interpolation. Values cannot contain quote/SQL characters.
    if database is None or not re.fullmatch(r"ase_test_[a-f0-9]{32}_(?:gw[0-9]+|master)", database):
        raise pytest.UsageError("Refusing a non-test PostgreSQL database identifier")
    connection = await asyncpg.connect(service.render_as_string(hide_password=False))
    try:
        verb = "CREATE" if create else "DROP"
        await connection.execute(f'{verb} DATABASE "{database}"')
    finally:
        await connection.close()


@pytest.fixture(scope="session", autouse=True)
def isolated_postgres_database(
    request: pytest.FixtureRequest, worker_id: str
) -> Iterator[str | None]:
    if not request.config.getoption("--isolated-postgres"):
        yield None
        return
    service = os.environ["ASE_TEST_DATABASE_URL"]
    private = worker_database_url(service, worker_id, uuid4().hex)
    asyncio.run(database_command(service, private, create=True))
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setenv("ASE_TEST_DATABASE_URL", private)
            yield private
    finally:
        # Only drop the database this fixture successfully created, never the service.
        asyncio.run(database_command(service, private, create=False))

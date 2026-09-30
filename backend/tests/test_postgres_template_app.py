"""The opt-in ordinary app sees one URL before setup and releases each test database."""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url


@pytest.fixture(autouse=True)
def require_template_option(request):
    if not request.config.getoption("--template-postgres"):
        pytest.skip("Exercises the explicit template PostgreSQL opt-in")


@pytest.fixture
def early_url():
    return os.environ["ASE_TEST_DATABASE_URL"]


async def test_url_precedes_settings_and_independent_fixture_consumers(
    early_url, settings, container, template_database, template_worker
):
    assert template_database is not None
    assert make_url(early_url) == make_url(settings.database_url) == container.engine.url
    assert template_worker._leases == {template_database.name: template_database}
    async with container.engine.begin() as connection:
        await connection.execute(text("INSERT INTO administration_lock DEFAULT VALUES"))


async def test_next_default_app_has_no_prior_rows_or_connections(
    container, template_database, template_worker
):
    assert template_database is not None
    assert template_worker._leases == {template_database.name: template_database}
    async with container.engine.begin() as connection:
        assert await connection.scalar(text("SELECT count(*) FROM administration_lock")) == 0
        assert (
            await connection.scalar(
                text("INSERT INTO administration_lock DEFAULT VALUES RETURNING id")
            )
            == 1
        )

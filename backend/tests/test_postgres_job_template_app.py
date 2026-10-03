"""The real report-job fixture chain keeps committed PostgreSQL transaction boundaries."""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from postgres_template_fixtures import _FUNCTIONS
from report_job_api_helpers import job_settings

__all__ = ["job_settings"]


@pytest.fixture(autouse=True)
def require_template_option(request):
    if not request.config.getoption("--template-postgres"):
        pytest.skip("Exercises the exact report-job template PostgreSQL opt-in")


async def test_job_chain_uses_a_clone_and_real_independent_transactions(
    settings, container, template_database, tmp_path, request
):
    assert template_database is not None
    worker = request.getfixturevalue("template_worker")
    assert worker._leases == {template_database.name: template_database}
    assert _FUNCTIONS["job_settings"](settings, tmp_path) is settings
    assert make_url(os.environ["ASE_TEST_DATABASE_URL"]) == container.engine.url
    assert make_url(settings.database_url) == make_url(template_database.url)
    async with container.session_factory() as writer, container.session_factory() as reader:
        await writer.execute(text("INSERT INTO administration_lock DEFAULT VALUES"))
        assert await reader.scalar(text("SELECT count(*) FROM administration_lock")) == 0
        await reader.rollback()
        await writer.commit()
        assert await reader.scalar(text("SELECT count(*) FROM administration_lock")) == 1
        await reader.rollback()
        await writer.execute(text("INSERT INTO administration_lock DEFAULT VALUES"))
        await writer.rollback()
        assert await reader.scalar(text("SELECT count(*) FROM administration_lock")) == 1


async def test_next_job_clone_has_no_prior_commits_leases_or_connections(
    container, template_database, request
):
    assert template_database is not None
    worker = request.getfixturevalue("template_worker")
    assert worker._leases == {template_database.name: template_database}
    async with container.session_factory() as session:
        assert await session.scalar(text("SELECT count(*) FROM administration_lock")) == 0
        assert (
            await session.scalar(
                text("INSERT INTO administration_lock DEFAULT VALUES RETURNING id")
            )
            == 1
        )

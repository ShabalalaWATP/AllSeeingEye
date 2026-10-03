"""Connector fixtures keep real app, storage, cancellation and disposal boundaries."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ase.adapters.notify.null_email import NullEmailSender
from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from event_app_fixtures import email_sender as _email_sender  # noqa: F401
from event_app_fixtures import feed_connectors as _feed_connectors  # noqa: F401
from feeds_helpers import FakeConnector, make_event, make_spec
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token

ORIGINAL_CASES = {
    "test_events_api": [
        "test_admin_sources_list_and_reset",
        "test_events_query_and_get",
        "test_events_query_validation",
        "test_map_news_indexing_window_does_not_change_publication_queries",
        "test_military_filter_precedes_page_limit_and_pagination_is_bounded",
        "test_stream_delivers_upserts_and_expiries",
        "test_stream_honours_the_token_expiry_and_the_per_user_cap",
        "test_stream_refuses_an_expired_token",
    ],
    "test_firms_source_inheritance": [
        f"{case}[{factory}]"
        for case in (
            "test_environment_parent_optout_is_visible_and_cannot_be_bypassed",
            "test_family_parent_controls_sql_admission_admin_listing_and_activation",
        )
        for factory in ("public_sensor_spec", "sensor_spec")
    ],
    "test_replan_source_activation": [
        "test_disabling_source_during_replan_blocks_second_underlying_fetch"
    ],
    "test_source_admission_cache": [
        "test_cached_flag_cannot_outlive_an_administrator_disable",
        "test_committed_switch_invalidates_before_expiry",
        "test_expiry_bounds_writes_made_outside_this_process",
        "test_repeated_checks_share_one_read",
        "test_switch_committed_during_a_reload_is_never_cached",
        "test_uncommitted_or_rolled_back_switches_never_stick",
    ],
    "test_source_controls": [
        "test_activation_persists_and_blocks_live_fetch",
        "test_admin_test_is_isolated_and_errors_are_safe",
        "test_controls_require_admin_and_known_source",
        "test_disabled_during_live_fetch_does_not_publish",
        "test_private_parent_admission_before_and_after_fetch[research_publisher_]",
        "test_private_parent_admission_before_and_after_fetch[research_regional_]",
        "test_source_tests_cap_counts_timeout_and_rate_limit",
        "test_test_release_rechecks_original_session",
        "test_variant_activation_rejects_a_disabled_parent",
    ],
    "test_source_release_race": [
        f"test_disable_waits_for_release_after_final_enabled_read[{private}-{cancelled}]"
        for private in (False, True)
        for cancelled in (False, True)
    ],
}


@pytest.fixture(autouse=True)
def disposed_pools():
    """Observe disposal after app finalisation without changing engine instrumentation."""
    observed = []
    yield observed
    for engine, original_pool in observed:
        assert engine.sync_engine.pool is not original_pool


@pytest.mark.parametrize("iteration", [0, 1])
async def test_fresh_connector_default_mailer_and_committed_storage(
    client, container, admin, email_sender, feed_connectors, disposed_pools, iteration
):
    disposed_pools.append((container.engine, container.engine.sync_engine.pool))
    assert email_sender is None
    assert isinstance(container.email_sender, NullEmailSender)
    assert not container.email_sender.available
    assert len(container.connectors) == 1
    connector = container.connectors[0]
    assert isinstance(connector, FakeConnector)
    assert connector.spec == make_spec("fake_feed")
    assert connector.calls == connector.failures == 0
    assert connector.events == [make_event()]
    assert feed_connectors[0] is connector
    assert container.scheduler.connectors == [connector]
    assert (await container.scheduler.poll_once(connector)).ok
    assert connector.calls == 1
    async with container.session_factory() as session:
        assert await SqlSourceControlRepository(session).all() == {}
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.patch(
        "/api/admin/sources/fake_feed/activation",
        headers=bearer(token),
        json={"enabled": False},
    )
    assert response.status_code == 204
    async with container.session_factory() as session:
        assert await SqlSourceControlRepository(session).all() == {"fake_feed": False}
    async with container.session_factory() as session:
        await SqlSourceControlRepository(session).set(
            "fake_feed", True, container.clock.now(), admin.id
        )
        await session.rollback()
    async with container.session_factory() as session:
        assert await SqlSourceControlRepository(session).all() == {"fake_feed": False}
    assert not (await container.scheduler.poll_once(connector)).ok
    assert connector.calls == 1


async def test_cancelled_source_write_rolls_back_and_releases_its_session(
    container, admin, disposed_pools
):
    disposed_pools.append((container.engine, container.engine.sync_engine.pool))
    flushed = asyncio.Event()
    release = asyncio.Event()

    async def write():
        async with container.session_factory() as session:
            await SqlSourceControlRepository(session).set(
                "fake_feed", False, container.clock.now(), admin.id
            )
            flushed.set()
            await release.wait()
            await session.commit()

    pending = asyncio.create_task(write())
    try:
        await asyncio.wait_for(flushed.wait(), 5)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
    finally:
        release.set()
        if not pending.done():
            pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
    async with container.session_factory() as session:
        assert await SqlSourceControlRepository(session).all() == {}
    assert await container.source_admission.enabled("fake_feed")


def test_real_source_items_keep_original_ids_and_cache_exclusions(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    observed = tmp_path / "source-items.json"
    plugin = tmp_path / "source_collection_probe.py"
    plugin.write_text(
        "import json, os\n"
        "from pathlib import Path\n"
        "def pytest_collection_finish(session):\n"
        "    from postgres_template_guard import ordinary_app\n"
        "    from database_markers import file_constructs_database\n"
        "    rows = [{'id': item.nodeid, 'eligible': ordinary_app(item),\n"
        "             'constructs': file_constructs_database(item.path),\n"
        "             'db': item.get_closest_marker('db') is not None}\n"
        "            for item in session.items]\n"
        "    Path(os.environ['SOURCE_COLLECTION_OUTPUT']).write_text(json.dumps(rows))\n",
        encoding="utf-8",
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("ASE_", "COVERAGE_", "COV_CORE_", "_COV_CORE_", "PYTEST_"))
    }
    environment.update(PYTHONPATH=str(tmp_path), SOURCE_COLLECTION_OUTPUT=str(observed))
    result = subprocess.run(  # noqa: S603 (fixed local test modules; no shell or external input)
        [
            sys.executable,
            "-m",
            "pytest",
            *(f"tests/{name}.py" for name in ORIGINAL_CASES),
            "--collect-only",
            "--no-cov",
            "-n",
            "0",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "source_collection_probe",
        ],
        cwd=backend,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    rows = json.loads(observed.read_text(encoding="utf-8"))
    expected = {
        f"tests/{module}.py::{name}" for module, names in ORIGINAL_CASES.items() for name in names
    }
    assert len(rows) == len(expected) == 32
    assert {row["id"] for row in rows} == expected
    assert all(row["db"] for row in rows)
    for row in rows:
        cache_case = row["id"].startswith("tests/test_source_admission_cache")
        assert row["eligible"] is not cache_case
        assert row["constructs"] is cache_case

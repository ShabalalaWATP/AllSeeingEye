"""The connection inventory says what is collecting and what is missing, never a secret."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

from ase.adapters.feeds.aisstream import SPEC as AISSTREAM_SPEC
from ase.adapters.feeds.cisa_kev import SPEC as KEV_SPEC
from ase.application.feeds.health import HealthRegistry, SourceStatus
from ase.application.source_inventory import (
    ConnectionState,
    SourceInventory,
    SourceRequirement,
)
from ase.container.research_sources import research_source_specs
from ase.domain.events import Category, Reliability
from ase.domain.sources import SourceKind, SourceSpec
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

NOW = datetime(2026, 9, 13, 12, tzinfo=UTC)
KEYED = SourceSpec(
    id="keyed_feed",
    name="Keyed feed",
    organisation="Example",
    category=Category.MARITIME,
    kind=SourceKind.API,
    url="https://example.test/feed",
    reliability=Reliability.B,
    poll_interval=timedelta(minutes=5),
    requires_key=True,
)
RESEARCH = SourceSpec(
    id="research-example",
    name="Example research",
    organisation="Example",
    category=Category.NEWS,
    kind=SourceKind.API,
    url="https://example.test/research",
    reliability=Reliability.F,
    poll_interval=timedelta(minutes=5),
)


def inventory(connectors=(), research=(), optional=(), requirements=None, disabled=(), health=None):
    admission = SimpleNamespace(
        enabled_many=AsyncMock(
            side_effect=lambda ids: {key: not key.startswith("off_") for key in ids}
        )
    )
    return SourceInventory(
        connectors,
        research,
        optional,
        requirements or {},
        health or HealthRegistry(),
        admission,
        disabled,
    )


async def test_missing_keyed_feeds_are_listed_with_their_setting_and_no_health():
    requirement = SourceRequirement(
        "api_key", False, "none", "ASE_EXAMPLE_KEY", "Set ASE_EXAMPLE_KEY on the server."
    )
    rows = await inventory(
        connectors=(SimpleNamespace(spec=KEV_SPEC),),
        optional=(KEYED,),
        requirements={KEYED.id: requirement},
    ).list()
    by_id = {row.spec.id: row for row in rows}
    keyed = by_id[KEYED.id].connection
    assert keyed.state is ConnectionState.KEY_MISSING
    assert keyed.active is False and keyed.health is None
    assert keyed.requirement is not None and keyed.requirement.setting == "ASE_EXAMPLE_KEY"
    assert by_id[KEYED.id].collection_mode == "scheduled"
    live = by_id[KEV_SPEC.id].connection
    assert live.state is ConnectionState.IDLE and live.active is True
    assert live.health is not None and live.health.status is SourceStatus.IDLE


async def test_health_and_credentials_map_to_states():
    health = HealthRegistry()
    healthy = health.get(KEV_SPEC.id)
    healthy.status, healthy.last_success = SourceStatus.HEALTHY, NOW
    degraded = health.get("off_degraded")
    degraded.status = SourceStatus.DEGRADED
    broken = health.get("broken")
    broken.status, broken.consecutive_failures = SourceStatus.DISABLED, 9
    unverified_spec = SourceSpec(
        id="keyed_live",
        name="Keyed live",
        organisation="Example",
        category=Category.MARITIME,
        kind=SourceKind.WEBSOCKET,
        url="wss://example.test",
        reliability=Reliability.B,
        poll_interval=timedelta(minutes=5),
        requires_key=True,
    )
    rows = await inventory(
        connectors=(
            SimpleNamespace(spec=KEV_SPEC),
            SimpleNamespace(spec=replace(KEYED, id="off_degraded")),
            SimpleNamespace(spec=replace(KEYED, id="broken")),
            SimpleNamespace(spec=unverified_spec),
        ),
        requirements={
            "keyed_live": SourceRequirement(
                "api_key", True, "environment", "ASE_LIVE_KEY", "Configured."
            ),
            "off_degraded": SourceRequirement(
                "api_key", True, "environment", "ASE_OFF_KEY", "Configured."
            ),
            "broken": SourceRequirement("api_key", True, "database", "ASE_BROKEN", "Configured."),
        },
        health=health,
    ).list()
    states = {row.spec.id: row.connection.state for row in rows}
    assert states[KEV_SPEC.id] is ConnectionState.CONNECTED
    assert states["off_degraded"] is ConnectionState.DISABLED_BY_ADMIN
    assert states["broken"] is ConnectionState.FAILING
    assert states["keyed_live"] is ConnectionState.KEY_UNVERIFIED


async def test_research_capabilities_report_on_demand_or_missing_requirements():
    snapshot = SourceRequirement(
        "snapshot", False, "none", "ASE_UKSL_SNAPSHOT_PATH", "Import a snapshot."
    )
    optional = SourceRequirement(
        "api_key", False, "none", "ASE_OPENALEX_API_KEY", "Optional.", optional=True
    )
    model = SourceRequirement("model", None, "unknown", None, "Uses the destination's model.")
    second = replace(RESEARCH, id="research-snapshot")
    third = replace(RESEARCH, id="research-model")
    fourth = replace(RESEARCH, id="research-env")
    rows = await inventory(
        research=(RESEARCH, second, third, fourth),
        requirements={"research-snapshot": snapshot, RESEARCH.id: optional, third.id: model},
        disabled=("research-env",),
    ).list()
    states = {row.spec.id: row.connection for row in rows}
    assert states[RESEARCH.id].state is ConnectionState.ON_DEMAND
    assert states["research-snapshot"].state is ConnectionState.NOT_CONFIGURED
    assert states["research-model"].state is ConnectionState.ON_DEMAND
    assert states["research-env"].state is ConnectionState.DISABLED_BY_ENVIRONMENT
    assert all(row.collection_mode == "on_demand" for row in rows)


async def test_catalogue_api_reports_connection_state_for_every_source(client, user):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.get("/api/sources", headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    items = {item["id"]: item for item in response.json()["items"]}
    assert AISSTREAM_SPEC.id in items
    ships = items[AISSTREAM_SPEC.id]
    assert ships["connection"]["state"] == "key_missing"
    assert ships["connection"]["requirement"]["setting"] == "ASE_AISSTREAM_API_KEY"
    assert ships["connection"]["health"] is None
    web = items["research-web-search"]["connection"]
    assert web["state"] == "on_demand" and web["requirement"]["kind"] == "model"
    house = items["research-companies-house"]["connection"]
    assert house["state"] == "key_missing" and house["requirement"]["kind"] == "api_key"
    openalex = items["research-openalex"]["connection"]
    assert openalex["state"] == "on_demand" and openalex["requirement"]["optional"] is True
    firms = items["firms_viirs_noaa20"]["connection"]
    assert firms["state"] == "key_missing"
    assert "ASE_FIRMS_MAP_KEY" in firms["requirement"]["setting"]
    live = items["usgs_earthquakes"]["connection"]
    assert live["active"] is True and live["health"]["status"] in {"idle", "healthy"}
    assert "last_error" not in live["health"] and "url" not in items["usgs_earthquakes"]
    assert set(items) >= {spec.id for spec in research_source_specs()}
    assert all(
        item["connection"]["state"]
        in {
            "connected",
            "idle",
            "degraded",
            "failing",
            "key_missing",
            "key_unverified",
            "on_demand",
            "not_configured",
            "disabled_by_admin",
            "disabled_by_environment",
        }
        for item in items.values()
    )


async def test_platform_connections_never_carry_values_and_flag_a_missing_model(client, user):
    assert (await client.get("/api/sources/connections")).status_code == 401
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.get("/api/sources/connections", headers=headers)
    assert response.status_code == 200, response.text
    rows = {row["id"]: row for row in response.json()["items"]}
    assert rows["assessment_model"]["state"] == "key_missing"
    assert rows["assessment_model"]["requirement"]["kind"] == "model"
    assert rows["os_maps"]["requirement"]["setting"] == "ASE_OS_MAPS_KEY"
    assert rows["email"]["state"] in {"connected", "key_missing"}
    assert rows["alert_webhook"]["requirement"]["optional"] is True
    assert {
        "credential_encryption",
        "highway_cameras",
        "url_archive",
        "conflict_screening",
        "media_tools",
        "pdf_runtime",
    } <= set(rows)
    # Requirements describe a setting name and a sentence, never a configured value.
    for row in rows.values():
        assert set(row["requirement"]) == {
            "kind",
            "satisfied",
            "origin",
            "setting",
            "note",
            "optional",
        }
        assert row["requirement"]["origin"] in {"environment", "database", "none", "unknown"}
        assert set(row) == {"id", "name", "purpose", "state", "requirement", "detail"}

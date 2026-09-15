"""The sources page lists every data family the app uses, with effective states and no secrets."""

from __future__ import annotations

import os
from datetime import timedelta

import pytest
from httpx import AsyncClient
from pydantic import SecretStr

from ase.adapters.feeds.acled_tokens import ENTITLEMENT_MESSAGE
from ase.adapters.feeds.conflict_reliefweb import APPNAME_NOT_APPROVED
from ase.adapters.feeds.conflict_reliefweb import SPEC as RELIEFWEB_SPEC
from ase.adapters.feeds.rss_access import AUTOMATION_REFUSALS
from ase.application.source_assets import snapshot_state
from ase.application.source_inventory import ConnectionState
from ase.container import Container
from ase.container.source_asset_cameras import _state, camera_assets
from ase.domain.cameras import CameraProviderStatus
from ase.domain.users import User
from ase.infrastructure.settings import Environment, Settings
from feeds_helpers import NOW
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

SECRETS = {
    "wsdot_access_code": "synthetic-wsdot-code-7731",
    "acled_refresh_token": "synthetic-acled-refresh-5512",
    "aisstream_api_key": "synthetic-aisstream-key-9034",
    "companies_house_key": "synthetic-companies-house-4471",
    "os_maps_key": "synthetic-os-maps-key-2208",
}
APPNAME = "synthetic-appname-6619"


@pytest.fixture
def settings() -> Settings:
    """A development-like server: feeds and archiving follow their defaults, keys are set."""
    return Settings(
        _env_file=None,
        env=Environment.DEV,
        database_url=os.environ.get("ASE_TEST_DATABASE_URL", "sqlite+aiosqlite://"),
        jwt_secret=SecretStr("t" * 40),
        encryption_key=SecretStr("e" * 40),
        public_base_url="http://app.test",
        cookie_secure=False,
        reliefweb_appname=APPNAME,
        ukraine_warspotting=True,
        **{key: SecretStr(value) for key, value in SECRETS.items()},
    )


async def _get(client: AsyncClient, path: str) -> tuple[dict, str]:
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    response = await client.get(path, headers=headers)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    return response.json(), response.text


async def test_assets_cover_cameras_maps_ukraine_and_reference_without_secrets(
    client: AsyncClient, user: User, container: Container
) -> None:
    assert (await client.get("/api/sources")).status_code == 401
    body, text = await _get(client, "/api/sources")
    connections = (await _get(client, "/api/sources/connections"))[1]
    for secret in (*SECRETS.values(), APPNAME):
        assert secret not in text and secret not in connections
    assets = {item["id"]: item for item in body["assets"]}
    families = {item["family"] for item in assets.values()}
    assert families == {"camera_index", "map_layer", "ukraine_dataset", "reference_dataset"}
    cameras = [item for item in assets.values() if item["family"] == "camera_index"]
    assert len(cameras) == len(container.cameras.sources) >= 90
    assert {
        "map:data_centres",
        "map:submarine_cables",
        "map:nuclear_facilities",
        "map:ground_stations",
        "map:military_source_index",
        "ukraine:viina_control",
        "ukraine:oryx_losses",
        "ukraine:hrmmu_casualties",
        "ukraine:deepstate",
        "reference:public_figures",
        "reference:entities",
    } <= set(assets)
    for item in assets.values():
        assert item["organisation"] and item["licence_note"] and item["coverage_note"]
        assert "url" not in item and "last_error" not in item
    assert assets["camera:tfl"]["delivery"] == "official_index"
    assert assets["camera:tfl"]["state"] == "on_demand"  # nothing is fetched to describe it
    assert assets["camera:uk-live"]["delivery"] == "curated_catalogue"
    assert assets["camera:uk-live"]["state"] == "available"
    assert assets["camera:eastasia"]["delivery"] == "third_party_directory"
    wsdot = assets["camera:wsdot"]
    assert wsdot["state"] == "on_demand" and wsdot["requirement"]["satisfied"] is True
    viina = assets["ukraine:viina_control"]
    assert viina["state"] == "available" and viina["as_of"] and viina["records"] > 0
    assert "ODbL" in viina["licence_note"]
    assert assets["ukraine:deepstate"]["state"] == "disabled_by_environment"
    assert assets["ukraine:deepstate"]["requirement"]["setting"] == "ASE_UKRAINE_DEEPSTATE_ACCESS"
    assert assets["ukraine:warspotting"]["state"] == "on_demand"
    # Keyed feeds carry the entitlement caveats that decide whether a key can work at all.
    items = {item["id"]: item for item in body["items"]}
    assert (
        "Research, Partner or Enterprise"
        in items["acled_events"]["connection"]["requirement"]["note"]
    )
    assert "pre-approved" in items[RELIEFWEB_SPEC.id]["connection"]["requirement"]["note"]


async def test_platform_toggles_report_the_effective_default(
    client: AsyncClient, user: User
) -> None:
    body, _ = await _get(client, "/api/sources/connections")
    rows = {row["id"]: row for row in body["items"]}
    for key in ("live_feeds", "url_archive", "conflict_screening"):
        assert rows[key]["state"] == "connected", rows[key]
        assert rows[key]["requirement"]["satisfied"] is True
    assert "on by default" in rows["url_archive"]["requirement"]["note"]
    assert "highway_cameras" not in rows  # the WSDOT key is reported on its camera provider


async def test_upstream_blocks_surface_their_fixed_reason(
    client: AsyncClient, user: User, container: Container
) -> None:
    for source_id, reason in (
        (RELIEFWEB_SPEC.id, APPNAME_NOT_APPROVED),
        ("cyber_cisa_advisories", AUTOMATION_REFUSALS["cyber_cisa_advisories"]),
        ("acled_events", ENTITLEMENT_MESSAGE),
    ):
        container.health.record_deferred(
            source_id, reason, NOW, NOW + timedelta(hours=12), blocked=True
        )
    container.health.record_deferred("usgs_earthquakes", "Cooldown at https://x.test", NOW, NOW)
    body, text = await _get(client, "/api/sources")
    items = {item["id"]: item["connection"] for item in body["items"]}
    for source_id, reason in (
        (RELIEFWEB_SPEC.id, APPNAME_NOT_APPROVED),
        ("cyber_cisa_advisories", AUTOMATION_REFUSALS["cyber_cisa_advisories"]),
        ("acled_events", ENTITLEMENT_MESSAGE),
    ):
        assert items[source_id]["state"] == "blocked_upstream"
        assert items[source_id]["detail"] == reason
        assert items[source_id]["health"]["blocked_reason"] == reason
    assert items["usgs_earthquakes"]["state"] == "degraded"
    assert items["usgs_earthquakes"]["health"]["blocked_reason"] is None
    assert "https://x.test" not in text


async def test_camera_states_follow_the_cache_and_a_missing_wsdot_code(
    container: Container, user: User
) -> None:
    def status(value: str, count: int = 4) -> CameraProviderStatus:
        return CameraProviderStatus("p", "P", value, count, NOW)  # type: ignore[arg-type]

    assert _state("official_index", status("available"))[::2] == (ConnectionState.CONNECTED, 4)
    assert _state("official_index", status("stale"))[0] is ConnectionState.DEGRADED
    assert _state("official_index", status("unavailable"))[::2] == (
        ConnectionState.DEGRADED,
        None,
    )
    assert _state("curated_catalogue", status("available"))[::2] == (
        ConnectionState.AVAILABLE,
        4,
    )
    missing = snapshot_state(False, "ase import-reference")
    assert missing[0] is ConnectionState.NOT_CONFIGURED and "ase import-reference" in missing[1]
    wsdot = next(
        item for item in camera_assets(container.cameras, user, False) if item.id == "camera:wsdot"
    )
    assert wsdot.state is ConnectionState.KEY_MISSING
    assert wsdot.requirement is not None and wsdot.requirement.setting == "ASE_WSDOT_ACCESS_CODE"

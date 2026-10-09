"""Policy-aware packaged data retains raw inventories without leaking restricted records."""

from ase.adapters.geo.area_geography import PackagedAreaGeography
from ase.application.map_assets import available_infrastructure
from ase.domain.source_licences import SourceLicence, SourceLicencePolicy
from test_asset_register_research import DUBLIN


def test_infrastructure_projection_preserves_allowed_rows_and_raw_snapshot():
    snapshot = {"cables": [{"name": "Cable"}], "ground_stations": [{"name": "Station"}]}
    policy = SourceLicencePolicy(
        (SourceLicence("map:submarine_cables", "allowed", True, "reference"),), commercial_use=True
    )
    result = available_infrastructure(snapshot, policy)
    assert result["cables"] == snapshot["cables"]
    assert result["ground_stations"] == []
    assert snapshot["ground_stations"] == [{"name": "Station"}]


def test_packaged_report_geography_does_not_release_denied_camera_records(monkeypatch):
    monkeypatch.setattr(
        "ase.adapters.geo.area_geography._cameras", lambda: (("tfl", "Road", -6.2, 53.35),)
    )
    service = PackagedAreaGeography(licences=SourceLicencePolicy((), commercial_use=True))
    result = service.assemble(area=DUBLIN, country_isos=(), cameras=True)
    assert result is not None
    assert result.registers == ()
    assert result.breakdown == ()
    assert "licence policy" in result.scope.limitation
    assert service.register_entries(area=DUBLIN, country_isos=(), classes=("data_centres",)) == ()

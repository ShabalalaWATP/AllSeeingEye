"""Camera metadata identifies each provider's geography without any provider requests."""

from unittest.mock import Mock

import pytest

from ase.adapters.geo.camera_http import CameraHttpClient
from ase.adapters.geo.camera_registry import build_sources
from ase.container.camera_coverage import CAMERA_COVERAGE
from ase.container.source_asset_cameras import camera_assets


@pytest.mark.parametrize(
    ("provider", "coverage"),
    [
        ("queensland", "Queensland, Australia"),
        ("puertorico", "Puerto Rico"),
        ("australia", "New South Wales, Australia"),
        ("iraq-iran-live", "Iraq and Iran"),
        ("china-live", "China"),
        ("israel-live", "Jerusalem"),
        ("caltrans", "California, United States"),
        ("ottawa", "Ottawa, Ontario, Canada"),
    ],
)
def test_provider_geography_is_not_inherited_from_adapter_family(provider, coverage):
    http = Mock(spec=CameraHttpClient)
    sources = build_sources(http, http)
    service = Mock(sources=sources)
    service.snapshot.return_value = Mock(providers=[])
    assets = {asset.id: asset for asset in camera_assets(service, Mock(), False)}
    assert assets[f"camera:{provider}"].coverage_note == coverage
    http.get_bytes.assert_not_called()
    http.get_json.assert_not_called()


def test_every_registered_camera_has_explicit_coverage():
    http = Mock(spec=CameraHttpClient)
    assert set(CAMERA_COVERAGE) == {source.id for source in build_sources(http, http)}
    assert all(value.strip() for value in CAMERA_COVERAGE.values())

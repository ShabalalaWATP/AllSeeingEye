"""New display policy is explicit and does not rewrite existing revision hashes."""

from dataclasses import replace

import pytest

from ase.api.schemas_map_views import MapStateFields
from ase.domain.map_view_records import revision_digest, state_from_dict, state_to_dict
from test_map_view_state import state


def test_display_upgrade_roundtrip_changes_only_explicit_policy():
    original = state()
    assert revision_digest(original, "Title", "version-1", "evidence-1") == (
        "55a80bc9bf85590eeafc47d44bfa7a23ed858d7f6045c8b730cc1ee16e3f2097"
    )
    upgraded = replace(original, display_transform="ase-geojson-display-v2")
    assert state_from_dict(state_to_dict(upgraded)) == upgraded
    assert (
        MapStateFields.model_validate(state_to_dict(upgraded)).display_transform
        == upgraded.display_transform
    )
    legacy = state_to_dict(original)
    current = state_to_dict(upgraded)
    assert {key for key in legacy if legacy[key] != current[key]} == {"display_transform"}
    assert revision_digest(original, "Title", "version-1", "evidence-1") != revision_digest(
        upgraded, "Title", "version-1", "evidence-1"
    )


@pytest.mark.parametrize("value", ["ase-geojson-display-v3", None, [], True])
def test_unknown_display_versions_are_rejected(value):
    with pytest.raises(ValueError):
        replace(state(), display_transform=value)

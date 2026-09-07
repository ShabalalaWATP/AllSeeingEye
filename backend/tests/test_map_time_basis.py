"""Explicit map temporal semantics preserve legacy canonical state and revision hashes."""

from dataclasses import replace

import pytest

from ase.api.schemas_map_views import MapStateFields
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.map_view_records import (
    canonical_state,
    revision_digest,
    state_from_dict,
    state_to_dict,
)
from test_map_view_state import state


def test_legacy_default_and_explicit_publication_have_identical_canonical_state():
    legacy = state_to_dict(state())
    assert "time_basis" not in legacy
    explicit = dict(legacy, time_basis="publication")
    transport_baseline = MapStateFields.model_validate(legacy).to_domain()
    for raw in (legacy, explicit):
        restored = state_from_dict(raw)
        assert restored.time_basis is EvidenceTimeBasis.PUBLICATION
        assert state_to_dict(restored) == legacy
        assert revision_digest(restored, "Title", "version-1", "evidence-1") == (
            "55a80bc9bf85590eeafc47d44bfa7a23ed858d7f6045c8b730cc1ee16e3f2097"
        )
        # The existing transport normalises camera numbers to floats. Compare like
        # representations rather than changing legacy integer serialisation.
        assert canonical_state(MapStateFields.model_validate(raw).to_domain()) == canonical_state(
            transport_baseline
        )


def test_acquisition_basis_is_frozen_and_changes_revision_identity():
    original = state()
    updated = replace(original, time_basis=EvidenceTimeBasis.RESEARCH)
    raw = state_to_dict(updated)
    assert raw["time_basis"] == "acquisition_or_publication"
    assert state_from_dict(raw) == updated
    assert MapStateFields.model_validate(raw).to_domain() == updated
    assert revision_digest(original, "Title", "v", "e") != revision_digest(
        updated, "Title", "v", "e"
    )
    assert original.time_basis is EvidenceTimeBasis.PUBLICATION


@pytest.mark.parametrize("basis", ["retrieval", "", None, True, [], {}])
def test_unknown_time_basis_is_rejected(basis):
    with pytest.raises(ValueError):
        state_from_dict(dict(state_to_dict(state()), time_basis=basis))

"""Frozen report DTOs preserve source observations without fabricated dates or points."""

from ase.adapters.research_records.copernicus_research import scene_event
from ase.api.schemas_report_evidence import ReportEvidenceOut
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_geometry import geometry_to_dict
from ase.domain.observation import observation_to_dict
from feeds_helpers import make_event
from test_copernicus_research import NOW
from test_copernicus_research_geometry import parse, payload


def test_frozen_observation_response_retains_geometry_and_separate_times():
    scene = parse(payload()).features[0]
    event = scene_event(scene, NOW)
    item = EvidenceItem.from_event("E1", event, NOW, source_name="Catalogue", independence_key="")
    response = ReportEvidenceOut.model_validate(item)
    assert response.geometry.model_dump(mode="json") == geometry_to_dict(item.geometry)
    assert response.observation.model_dump()["acquired_at"] == item.observation.acquired_at
    assert response.observation.processed_at is None
    assert response.published_at is None and response.lon is None and response.lat is None
    assert response.observed_at == NOW and response.captured_at == NOW
    assert (
        response.observation.collection_id == observation_to_dict(item.observation)["collection_id"]
    )


def test_legacy_evidence_response_has_no_invented_observation():
    item = EvidenceItem.from_event("E1", make_event(), NOW, source_name="Feed", independence_key="")
    response = ReportEvidenceOut.model_validate(item)
    assert response.geometry is None and response.observation is None
    assert response.published_at == item.published_at

"""The brief API accepts the existing map GeoJSON shape without client-side hashes."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ase.api.schemas_research_briefs import ResearchBriefDraftIn
from ase.domain.research_area import ResearchArea
from ase.domain.research_brief_values import BriefIdentity, BriefValidationError
from test_direct_area_research import area_input
from test_map_research_origin import AREA
from test_research_brief_api import _draft


def _identity() -> BriefIdentity:
    now = datetime(2026, 9, 14, tzinfo=UTC)
    return BriefIdentity(uuid4(), 1, uuid4(), "Area brief", now, now)


def test_plain_map_geometry_is_canonicalised_by_brief_api() -> None:
    draft = _draft()
    draft["scope"]["area"] = area_input()
    brief = ResearchBriefDraftIn.model_validate(draft).to_brief(_identity())
    assert brief.scope.area == ResearchArea(AREA)
    assert brief.scope.area.geometry.sha256 == AREA.sha256


def test_mismatched_supplied_area_hash_is_rejected() -> None:
    draft = _draft()
    draft["scope"]["area"] = {**area_input(), "sha256": "0" * 64}
    with pytest.raises(BriefValidationError):
        ResearchBriefDraftIn.model_validate(draft).to_brief(_identity())

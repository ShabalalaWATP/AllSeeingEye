"""Report handoff provenance is separate from an inherited analytic follow-up."""

from dataclasses import replace
from uuid import uuid4

import pytest

from ase.application.research.brief_codec import brief_from_dict, brief_to_dict
from ase.application.research.brief_conversion import run_request_from_brief
from ase.domain.research_brief_scope import BriefScope
from ase.domain.research_brief_values import BriefValidationError
from test_research_brief_persistence import NOW, _brief


def test_origin_version_survives_brief_without_freezing_future_window() -> None:
    report_id = uuid4()
    source = _brief()
    scope = replace(source.scope, origin_report_id=report_id, origin_version=3)
    brief = replace(source, scope=scope)
    assert brief_from_dict(brief_to_dict(brief)) == brief
    request = run_request_from_brief(brief, now=NOW)
    assert request.parent_report_id is None
    assert request.research_since is None


def test_origin_requires_an_exact_version() -> None:
    with pytest.raises(BriefValidationError):
        BriefScope(origin_report_id=uuid4())

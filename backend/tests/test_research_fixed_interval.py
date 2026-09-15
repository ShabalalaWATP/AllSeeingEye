"""Fixed area research intervals retain precision and actual capture time."""

from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from ase.adapters.store.memory import InMemoryEventStore
from ase.api.schemas_reports import ReportCreateIn
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import template_for
from ase.domain.evidence_time import EvidenceTimeBasis
from feeds_helpers import NOW
from test_evidence_time import scene


def payload():
    return {
        "template": "ask",
        "question": "What was observed?",
        "research_mode": "quick",
        "map_view_id": str(uuid4()),
        "map_revision_id": str(uuid4()),
        "disclose_area_to_provider": True,
        "research_since": "2020-01-01T10:00:00.123456Z",
        "research_until": "2020-01-01T10:20:00.654321Z",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"research_until": None},
        {"research_since": None},
        {"research_since": "2020-01-01T10:00:00"},
        {"research_until": "2020-01-01T10:00:00.123456Z"},
        # Longer than the 730-day research maximum.
        {"research_until": "2022-01-02T10:00:00Z"},
        {"window_hours": 1},
        {"map_view_id": None},
        {"disclose_area_to_provider": "true"},
    ],
)
def test_rejects_invalid_fixed_interval_before_application(change):
    with pytest.raises(ValidationError):
        ReportCreateIn.model_validate({**payload(), **change})


def test_fixed_interval_without_research_mode_is_accepted():
    # Subscription editions pin exact windows for reports that do not research.
    accepted = ReportCreateIn.model_validate({**payload(), "research_mode": None})
    assert accepted.research_mode is None and accepted.research_since is not None


def test_transport_retains_exact_map_and_interval():
    body = payload()
    request = ReportCreateIn.model_validate(body).to_request()
    assert request.research_since.microsecond == 123456
    assert request.research_until.microsecond == 654321
    assert str(request.map_revision_id) == body["map_revision_id"]
    assert request.disclose_area_to_provider is True


def test_subhour_historical_selection_includes_start_excludes_end_and_captures_now():
    request = ReportCreateIn.model_validate(payload()).to_request()
    start, end = request.research_since, request.research_until
    store = InMemoryEventStore()
    store.upsert(
        [
            scene("start", start),
            scene("before", start - timedelta(microseconds=1)),
            scene("last", end - timedelta(microseconds=1)),
            scene("end", end),
        ]
    )
    selected = select_evidence(
        store,
        {},
        template_for("ask").strategy,
        now=NOW,
        since=start,
        until=end,
        time_basis=EvidenceTimeBasis.RESEARCH,
    )
    assert [item.event_id for item in selected.items] == [
        scene("last", end - timedelta(microseconds=1)).id,
        scene("start", start).id,
    ]
    assert all(item.captured_at == NOW for item in selected.items)

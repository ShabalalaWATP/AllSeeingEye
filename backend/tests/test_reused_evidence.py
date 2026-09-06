"""Follow-up selection retains historical grades and provenance without regrading."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.reused_evidence import with_reused_evidence
from ase.application.reports.selection import Selection
from ase.domain.events import Category
from ase.domain.research import ResearchFocus
from feeds_helpers import make_event
from production_integration_helpers import production_job
from report_documents_helpers import document_records


def test_reuse_preserves_original_data_relabels_and_wins_duplicate_ids():
    _, version = document_records()
    first = replace(
        version.evidence[0], label="E99", published_at=version.created_at - timedelta(days=365)
    )
    fresh = replace(first, label="E1", title="A changed live item", reliability="F")
    selected = Selection((fresh, version.evidence[1]), 0, 2)
    result = with_reused_evidence(selected, (first,))
    assert result.items == (replace(first, label="E1"), replace(version.evidence[1], label="E2"))
    assert result.items[0].published_at < version.created_at - timedelta(days=300)


def test_reuse_is_bounded_and_does_not_silently_drop_frozen_inputs():
    _, version = document_records()
    rows = tuple(replace(version.evidence[0], event_id=str(index)) for index in range(101))
    with pytest.raises(ValueError, match="evidence limit"):
        with_reused_evidence(Selection((), 0, 0), rows)
    result = with_reused_evidence(Selection((rows[100],), 0, 1), rows[:100])
    assert len(result.items) == 100
    assert result.considered == 100


@pytest.mark.parametrize("focus", [ResearchFocus.DOCUMENT, ResearchFocus.MEDIA])
async def test_supplied_private_inputs_are_not_dropped_by_news_scope_filters(
    container, user, focus
):
    job = production_job(user, container.cipher)
    event = make_event(
        title="A supplied historic passage",
        category=Category.NEWS,
        point=None,
        country_iso=None,
        published_at=job.now - timedelta(days=365),
    )
    job = replace(
        job,
        seed_events=(event,),
        request=replace(
            job.request, research_focus=focus, country_iso="UA", categories=(Category.DISASTER,)
        ),
    )
    store = InMemoryEventStore()
    store.upsert((event,))
    selected = select_for_job(store, {}, job, None)
    assert len(selected.items) == 1
    assert selected.items[0].published_at == event.published_at
    assert selected.items[0].category == Category.NEWS
    assert selected.items[0].country_iso is None

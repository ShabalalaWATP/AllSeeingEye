"""Source-origin filing declarations survive bounded first operator amendments."""

from dataclasses import replace
from uuid import uuid4

import pytest

from ase.domain.errors import InvalidRequest
from ase.domain.input_declarations import (
    InputPassageDeclaration,
    InputSourceDate,
    apply_declarations,
)
from ase.domain.sec_filing_time import filing_source_date
from ase.domain.text_transformations import TextTransformation
from research_input_helpers import Harness, extracted


def source_event():
    event = extracted(text=b"Issuer 2026-08-31").events[0]
    return replace(event, source_dates=(filing_source_date("2026-08-31"),))


def transformation(event, origin="source"):
    return TextTransformation(
        "summary",
        event.summary,
        "Issuer",
        "transliteration",
        "en",
        "en",
        origin,
        "Declared source transcription",
        "Latn",
        "Latn",
    )


@pytest.mark.parametrize("kind", ["dates", "transformations"])
@pytest.mark.parametrize("count", [3, 4])
async def test_combined_bounds_preserve_source_rows_and_release_failed_reservation(kind, count):
    h = Harness()
    event = source_event()
    if kind == "transformations":
        event = replace(event, transformations=(transformation(event),))
    base = replace(extracted(text=b"Issuer 2026-08-31"), events=(event,))
    reservation = h.store.reserve(h.actor, "notes.txt")
    original = h.store.put(reservation, base)
    h.store.release(reservation)
    row = InputPassageDeclaration(
        event.id,
        event.content_hash,
        transformations=(transformation(event, "operator"),) * count
        if kind == "transformations"
        else (),
        source_dates=(InputSourceDate("summary", "2026-08-31", "occurrence", "gregorian"),) * count
        if kind == "dates"
        else (),
    )
    if count == 4:
        with pytest.raises(InvalidRequest, match="four"):
            await h.service.declare(h.actor, original.receipt.id, original.receipt.sha256, (row,))
        # An unsuccessful declaration neither retains a derivative nor consumes its slot.
        replacement = h.store.reserve(h.actor, "another.txt")
        h.store.release(replacement)
    else:
        receipt = await h.service.declare(
            h.actor, original.receipt.id, original.receipt.sha256, (row,)
        )
        new = h.store.read(h.actor, receipt.id).events[0]
        assert new.source_dates[:1] == event.source_dates
        assert new.summary == event.summary and new.content_hash == event.content_hash
        if kind == "dates":
            assert len(new.source_dates) == 4
            assert all(item.actor_id == h.actor.id for item in new.source_dates[1:])
        else:
            assert new.transformations[:1] == event.transformations
            assert len(new.transformations) == 4
            assert all(item.actor_id == h.actor.id for item in new.transformations[1:])
        with pytest.raises(ValueError):
            apply_declarations((new,), (row,), h.actor.id)
    assert h.store.read(h.actor, original.receipt.id) == original


def test_operator_cannot_replace_source_publication_day_with_an_invented_instant():
    event = replace(source_event(), summary="2026-08-31T12:00:00Z")
    row = InputPassageDeclaration(
        event.id,
        event.content_hash,
        source_dates=(InputSourceDate("summary", event.summary, "publication", "gregorian"),),
    )
    result = apply_declarations((event,), (row,), uuid4())[0]
    assert result.source_dates[0] == event.source_dates[0]
    assert len(result.source_dates) == 2 and result.published_at is None


@pytest.mark.parametrize("kind", ["date", "transformation"])
def test_existing_operator_provenance_refused_even_below_combined_caps(kind):
    event = source_event()
    if kind == "date":
        event = replace(event, source_dates=(replace(event.source_dates[0], basis="operator"),))
    else:
        event = replace(event, transformations=(transformation(event, "operator"),))
    row = InputPassageDeclaration(
        event.id, event.content_hash, transformations=(transformation(event, "operator"),)
    )
    with pytest.raises(ValueError, match="undeclared"):
        apply_declarations((event,), (row,), uuid4())

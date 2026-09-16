"""Every item reaching the model states its viewpoint, remit and observation date."""

from dataclasses import replace
from datetime import UTC, datetime

from ase.application.reports.prompts import doctrine_preamble, evidence_block
from ase.application.reports.source_character import MAX_REMIT_CHARS, source_character
from ase.domain.events import Reliability
from ase.domain.source_ratings import source_rating_for, unassessed_source_rating
from report_documents_helpers import document_records

NOW = datetime(2026, 9, 5, tzinfo=UTC)


def item(**changes):
    _, version = document_records()
    base = replace(
        version.evidence[0],
        observed_at=datetime(2026, 9, 4, 21, tzinfo=UTC),
        source_rating=unassessed_source_rating(),
    )
    return replace(base, **changes)


def test_a_state_aligned_outlet_is_visible_as_such_in_the_prompt():
    block = evidence_block(
        item(
            source_id="tass_en",
            source_name="TASS English",
            independence_key="tass",
            flags=("state_controlled",),
            source_rating=source_rating_for("tass_en", Reliability.D),
        )
    )
    assert "state-aligned outlet, so treat its claims as the state's position" in block
    assert "organisation tass" in block
    assert "observed 2026-09-04 21:00 UTC" in block
    assert "remit: " in block


def test_a_participant_source_is_named_as_an_interested_party():
    block = evidence_block(item(flags=("interested_party",)))
    assert "participant or interested party in what it reports" in block


def test_an_unassessed_source_stays_unassessed_and_states_no_remit():
    text = source_character(item())
    assert "viewpoint not assessed" in text
    assert "source reliability unassessed" in text
    assert "Unassessed source identity and publication context." in text


def test_an_editorial_rating_reports_its_inherited_grade_and_standing():
    rating = source_rating_for("bbc_world", Reliability.B)
    text = source_character(item(source_id="bbc_world", source_rating=rating))
    if rating.status == "editorial":
        assert f"inherited editorial grade {rating.assessed_grade.value}" in text
        assert rating.provenance_role in ("originator", "publisher", "aggregator", "platform")
    else:
        assert "source reliability unassessed" in text


def test_the_remit_stays_bounded_and_the_clause_is_one_sentence():
    long_rating = replace(unassessed_source_rating(), scope="r" * 400)
    text = source_character(item(source_rating=long_rating))
    assert "r" * MAX_REMIT_CHARS in text
    assert "r" * (MAX_REMIT_CHARS + 1) not in text
    assert text.count("Source character:") == 1 and text.endswith(".")


def test_an_item_without_an_observation_date_omits_it_rather_than_inventing_one():
    text = source_character(item(observed_at=None))
    assert "observed" not in text


def test_the_doctrine_preamble_tells_the_model_what_source_character_means():
    preamble = doctrine_preamble()
    assert "source character" in preamble
    assert "official issuer, publisher, aggregator, platform, state-aligned outlet" in preamble

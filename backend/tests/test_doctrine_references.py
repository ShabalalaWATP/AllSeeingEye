"""Offline integrity and scope checks for the manually verified public doctrine pack."""

import hashlib
from dataclasses import FrozenInstanceError, replace
from datetime import date

import pytest

from ase.application.assistant.catalogues import doctrine_sources
from ase.application.assistant.doctrine_references import (
    DOCTRINE_REFERENCE_PACK_SHA256,
    DOCTRINE_REFERENCES,
)
from ase.application.assistant.intent import interpret_question
from ase.domain.assistant import AssistantQuestion, AssistantSelection, AssistantTimeRange
from ase.domain.doctrine_reference import reference_pack_sha256, validate_reference_pack
from ase.domain.events import BoundingBox
from feeds_helpers import NOW


def test_pinned_registry_and_each_attributed_excerpt_are_intact():
    validate_reference_pack(DOCTRINE_REFERENCES, DOCTRINE_REFERENCE_PACK_SHA256)
    assert reference_pack_sha256(DOCTRINE_REFERENCES) == DOCTRINE_REFERENCE_PACK_SHA256
    assert len({reference.identifier for reference in DOCTRINE_REFERENCES}) == 4
    assert {reference.retrieved_on for reference in DOCTRINE_REFERENCES} == {date(2026, 9, 14)}
    for reference in DOCTRINE_REFERENCES:
        excerpt = reference.excerpt
        assert hashlib.sha256(excerpt.text.encode("utf-8")).hexdigest() == excerpt.sha256
        assert 0 < len(excerpt.text.split()) <= 25
        assert excerpt.source_url and excerpt.locator and excerpt.reuse_basis


def test_registry_does_not_overstate_mod_date_precision_or_nato_text_verification():
    phia, standards, mod, nato = DOCTRINE_REFERENCES
    assert phia.publication_date == standards.publication_date == "2025-03-24"
    assert phia.verification_scope == standards.verification_scope == "public_guidance"
    assert mod.edition == "Fourth Edition"
    assert mod.publication_date == "2023-08" and mod.date_basis == "edition_month"
    assert mod.catalogue_published_on == date(2011, 8, 1)
    assert mod.catalogue_updated_on == date(2023, 8, 17)
    assert mod.publication_url.endswith("/JDP_2_00_Ed_4_web.pdf")
    assert mod.excerpt.source_url == mod.url
    assert "PDF" in mod.access_note and "separate" in mod.access_note
    assert nato.edition == "Edition B" and nato.version is None
    assert nato.publication_date == "2025-08-20" and nato.date_basis == "promulgation"
    assert nato.verification_scope == "catalogue_metadata"
    assert nato.catalogue_updated_on is None
    assert nato.publication_url is None
    assert nato.url == "https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=283399"
    assert "Controlled distribution" in nato.access_note
    assert "not retrieved or verified" in nato.access_note


@pytest.mark.parametrize("field", ["text", "sha256"])
def test_excerpt_changes_require_a_matching_explicit_digest(field):
    excerpt = DOCTRINE_REFERENCES[0].excerpt
    value = excerpt.text + " " if field == "text" else "0" * 64
    with pytest.raises(ValueError, match="hash"):
        replace(excerpt, **{field: value})


@pytest.mark.parametrize("change", ["edition", "url", "date", "order", "duplicate"])
def test_pack_hash_covers_metadata_order_and_unique_identity(change):
    rows = DOCTRINE_REFERENCES
    if change == "edition":
        rows = (replace(rows[0], edition="Different edition"), *rows[1:])
    elif change == "url":
        rows = (replace(rows[0], url="https://www.gov.uk/another-page"), *rows[1:])
    elif change == "date":
        rows = (replace(rows[0], retrieved_on=date(2026, 9, 15)), *rows[1:])
    elif change == "order":
        rows = tuple(reversed(rows))
    else:
        rows = (*rows, rows[0])
    with pytest.raises(ValueError, match="pack"):
        validate_reference_pack(rows, DOCTRINE_REFERENCE_PACK_SHA256)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.gov.uk/example",
        "https://www.gov.uk.evil.example/example",
        "https://user@www.gov.uk/example",
        "https://www.gov.uk:443/example",
        "https://mirror.example/publication.pdf",
        "https://www.gov.uk/invalid path",
    ],
)
def test_registry_urls_cannot_silently_switch_to_unverified_hosts_or_credentials(url):
    with pytest.raises(ValueError, match="official HTTPS"):
        replace(DOCTRINE_REFERENCES[0], url=url)


@pytest.mark.parametrize(
    "changes",
    [
        {"publication_date": "2023-08-01"},
        {"publication_date": "2023-13"},
        {"date_basis": "guessed"},
        {"retrieved_on": date(2020, 1, 1)},
        {"catalogue_updated_on": date(2099, 1, 1)},
        {"version": ""},
        {"verification_scope": "fully_compliant"},
    ],
)
def test_invalid_or_invented_verification_metadata_is_rejected(changes):
    with pytest.raises(ValueError):
        replace(DOCTRINE_REFERENCES[2], **changes)


def test_catalogue_only_source_cannot_gain_an_unverified_publication_link():
    with pytest.raises(ValueError, match="Catalogue-only"):
        replace(DOCTRINE_REFERENCES[-1], publication_url=DOCTRINE_REFERENCES[2].publication_url)


def test_registry_records_and_excerpts_cannot_be_mutated():
    with pytest.raises(FrozenInstanceError):
        DOCTRINE_REFERENCES[0].edition = "Changed"
    with pytest.raises(FrozenInstanceError):
        DOCTRINE_REFERENCES[0].excerpt.text = "Changed"


@pytest.mark.parametrize(
    ("text", "identifiers"),
    [
        ("Explain doctrine", {"uk-mod-jdp-2-00", "nato-ajp-2-9-catalogue"}),
        ("Explain PHIA doctrine", {"phia-uncertainty-2025", "phia-standards-2025"}),
        ("Explain the yardstick", {"phia-uncertainty-2025"}),
    ],
)
def test_ask_eye_receives_verified_metadata_without_event_dates_or_grades(text, identifiers):
    question = AssistantQuestion(text)
    sources = doctrine_sources(question, interpret_question(question.question))
    assert {source.record_id for source in sources} == identifiers
    references = {reference.identifier: reference for reference in DOCTRINE_REFERENCES}
    for source in sources:
        reference = references[source.record_id]
        assert source.kind == "doctrine"
        assert source.grade is source.point is source.published_at is source.observed_at is None
        assert source.url == reference.url
        assert reference.publication_date in " ".join(source.details)
        assert reference.edition in " ".join(source.details)
        assert "2026-09-14" in " ".join(source.details)
        assert reference.access_note in source.details
        assert "Methodology reference, not event evidence." in source.details


@pytest.mark.parametrize("scope", ["selected", "viewport", "time", "event"])
def test_methodology_pack_does_not_become_spatial_or_time_filtered_incident_evidence(scope):
    changes = {}
    text = "Explain doctrine"
    if scope == "selected":
        changes = {"scope": "selected", "selected": AssistantSelection("event", "test-event")}
    elif scope == "viewport":
        changes = {"scope": "viewport", "bbox": BoundingBox(-1, -1, 1, 1)}
    elif scope == "time":
        changes = {"time_range": AssistantTimeRange(NOW.replace(hour=0), NOW.replace(hour=1))}
    else:
        text = "Earthquakes in Japan"
    question = AssistantQuestion(text, **changes)
    assert doctrine_sources(question, interpret_question(text)) == []

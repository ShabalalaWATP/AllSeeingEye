"""Exact source passages, correction lineage and scoped citation integrity."""

import hashlib
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.application.research.original_passages import (
    MAX_EXCERPT_BYTES,
    extracted_version,
    require_original_passage,
    translated_derivative,
)
from ase.domain.errors import InvalidRequest, NotFound
from original_acquisition_support import (
    NOW,
    access,
    catalogue,
    extraction,
    policy,
    response,
)


def version(*, source=None, body=b"exact original", result=None, parsed=None, previous=None):
    source = source or catalogue()
    candidate = next(iter(source.candidates.values()))
    result = result or response(body)
    parsed = parsed or extraction(body)
    return extracted_version(candidate, result, parsed, policy(), NOW, previous=previous)


def read(document, *, source, **changes):
    options = {
        "catalogue": source,
        "access": access(source.owner_id),
        "now": NOW,
        "source_enabled": True,
        "revoked": False,
    }
    return require_original_passage(document, document.passages[0].id, **(options | changes))


def test_exact_unicode_offsets_and_pdf_page_reference_are_hash_bound():
    body = b"offline PDF fixture bytes"
    text = "Exact café passage.\nSecond line."
    result = response(body, media_type="application/pdf", last_modified_at=NOW, etag='"v1"')
    parsed = extraction(
        body, "original.pdf", ("PDF page 7, characters 1801-1833",), (text,), "application/pdf"
    )
    document = version(body=body, result=result, parsed=parsed)
    passage = document.passages[0]
    assert passage.text == text
    assert passage.start == 0 and passage.end == len(text)
    assert passage.unit_index == 0 and passage.page == 7
    assert passage.offset_basis == "extracted_unit_unicode_codepoints"
    assert passage.source_reference == "PDF page 7, characters 1801-1833"
    assert passage.original_sha256 == hashlib.sha256(body).hexdigest()
    assert passage.text_sha256 == hashlib.sha256(text.encode()).hexdigest()
    assert document.published_at is None and document.http_last_modified_at == NOW
    assert document.update_basis == "http_last_modified_not_publication_time"
    assert document.etag == '"v1"' and document.original_language == "und"
    assert document.expires_at == NOW + timedelta(days=1)


def test_correction_creates_new_version_without_mutating_frozen_history():
    source = catalogue()
    first = version(source=source)
    second = version(source=source, body=b"corrected original", previous=first)
    assert second.id != first.id and second.sha256 != first.sha256
    assert second.previous_sha256 == first.sha256
    assert first.previous_sha256 is None and first.passages[0].text == "exact original"
    unchanged = version(source=source, previous=first)
    assert unchanged.id == first.id and unchanged.previous_sha256 is None
    assert second.passages[0].id != first.passages[0].id
    for previous in (
        replace(first, source_id="different"),
        replace(first, canonical_url="https://publisher.example/another"),
        replace(first, owner_id=uuid4()),
    ):
        with pytest.raises(ValueError):
            version(source=source, previous=previous)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: replace(value, sha256="invented"),
        lambda value: replace(value, media_type="text/html"),
        lambda value: replace(value, events=()),
        lambda value: replace(value, parent_input_id=uuid4()),
        lambda value: replace(value, parent_input_ids=(uuid4(),)),
        lambda value: replace(value, events=(replace(value.events[0], subtype="summary"),)),
        lambda value: replace(value, events=(replace(value.events[0], attributes={}),)),
        lambda value: replace(value, events=(replace(value.events[0], summary=None),)),
        lambda value: replace(value, events=(replace(value.events[0], summary="\x00text"),)),
        lambda value: replace(value, events=(replace(value.events[0], summary="  "),)),
        lambda value: replace(value, events=(replace(value.events[0], summary="x" * 1801),)),
    ],
)
def test_invalid_parser_provenance_or_unbounded_passage_is_rejected(mutate):
    body = b"exact original"
    with pytest.raises(ValueError):
        version(body=body, parsed=mutate(extraction(body)))


def test_passage_count_and_utf8_excerpt_bytes_are_bounded_with_explicit_omissions():
    body = b"bounded fixture"
    refs = tuple(f"Text line {index}" for index in range(80))
    parsed = extraction(body, references=refs, texts=("exact",) * 80)
    document = version(body=body, parsed=parsed)
    assert len(document.passages) == 40 and document.omitted_passages == 40
    dense = extraction(body, references=refs, texts=("界" * 1800,) * 80)
    document = version(body=body, parsed=dense)
    assert sum(len(item.text.encode()) for item in document.passages) <= MAX_EXCERPT_BYTES
    assert len(document.passages) == 12 and document.omitted_passages == 68
    assert all(item.page is None for item in document.passages)


def test_original_citation_requires_current_scope_and_unexpired_unrevoked_source():
    source = catalogue()
    document = version(source=source)
    assert read(document, source=source) == document.passages[0]
    for changes in (
        {"source_enabled": False},
        {"revoked": True},
        {"now": document.expires_at},
        {"access": access(uuid4())},
    ):
        with pytest.raises(NotFound):
            read(document, source=source, **changes)
    with pytest.raises(NotFound):
        read(replace(document, source_id="different"), source=source)
    with pytest.raises(NotFound):
        read(replace(document, owner_id=uuid4()), source=source)
    with pytest.raises(NotFound):
        require_original_passage(
            document,
            "unknown-passage",
            catalogue=source,
            access=access(source.owner_id),
            now=NOW,
            source_enabled=True,
            revoked=False,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"text": "edited passage"},
        {"text_sha256": "invented"},
        {"end": 999},
        {"start": 1},
        {"source_reference": "invented locator"},
        {"page": 8},
        {"original_sha256": "invented"},
        {"document_version_id": "invented"},
    ],
)
def test_citation_integrity_rejects_modified_passage_metadata(changes):
    source = catalogue()
    document = version(source=source)
    altered = replace(document.passages[0], **changes)
    with pytest.raises(InvalidRequest):
        read(replace(document, passages=(altered,)), source=source)


def test_translation_remains_a_separately_labelled_derivative_of_exact_original():
    source = catalogue()
    document = version(source=source)
    original = document.passages[0]
    translated = translated_derivative(original, "passage traduit", language="fr", method="human")
    assert translated.content_kind == "translated_derivative"
    assert translated.original_passage_id == original.id
    assert translated.original_text_sha256 == original.text_sha256
    assert translated.text_sha256 == hashlib.sha256(b"passage traduit").hexdigest()
    assert read(document, source=source).text == "exact original"
    assert translated.id != original.id


@pytest.mark.parametrize(
    "changes",
    [
        {"language": "invented language"},
        {"text": " "},
        {"text": "x" * 1801},
        {"method": ""},
        {"method": "unsafe\x00method"},
        {"text": "unsafe\x00translation"},
    ],
)
def test_invalid_translation_metadata_is_rejected(changes):
    values = {"text": "translated", "language": "en", "method": "human"}
    with pytest.raises(ValueError):
        translated_derivative(version().passages[0], **(values | changes))


def test_translation_cannot_attach_to_a_modified_original_passage():
    original = replace(version().passages[0], text="edited original")
    with pytest.raises(ValueError):
        translated_derivative(original, "translated", language="en", method="human")

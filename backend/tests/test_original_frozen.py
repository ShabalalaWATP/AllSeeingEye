"""Frozen selected original excerpts keep exact provenance without raw archiving."""

import json
from copy import deepcopy

import pytest

from ase.application.research.original_frozen import (
    freeze_selected_original,
    frozen_original_from_dict,
)
from ase.application.research.original_passages import require_original_passage
from ase.domain.errors import NotFound
from original_acquisition_support import NOW, Harness, extraction, response


async def test_selected_passage_roundtrips_without_unselected_or_original_bytes():
    harness = Harness()

    async def two_units(body, filename, captured_at):
        return extraction(
            body,
            filename,
            references=("Text line 1", "Text line 2"),
            texts=("First original unit", "Second original unit"),
        )

    harness.parser.extract = two_units
    acquired = await harness.acquire()
    first, second = acquired.document.passages
    frozen = freeze_selected_original(acquired.document, (second.id,))
    assert frozen["schema_version"] == 1
    assert len(frozen["document"]["passages"]) == 1
    assert frozen["document"]["omitted_passages"] == 1
    assert "original_bytes" not in frozen["document"]
    assert "body" not in frozen["document"]
    assert "First original unit" not in json.dumps(frozen)
    restored = frozen_original_from_dict(json.loads(json.dumps(frozen)))
    assert restored.passages == (second,)
    assert restored.published_at is None
    assert restored.original_language == "und"
    assert restored.requirement_ids == ("q1",)
    assert freeze_selected_original(restored, (second.id,)) == frozen
    assert (
        require_original_passage(
            restored,
            second.id,
            catalogue=harness.catalogue,
            access=harness.access,
            now=NOW,
            source_enabled=True,
            revoked=False,
        )
        == second
    )
    with pytest.raises(NotFound):
        require_original_passage(
            restored,
            first.id,
            catalogue=harness.catalogue,
            access=harness.access,
            now=NOW,
            source_enabled=True,
            revoked=False,
        )


async def test_correction_is_a_new_frozen_version_linked_to_prior_hash():
    harness = Harness()
    previous = (await harness.acquire()).document
    previous_snapshot = freeze_selected_original(previous, (previous.passages[0].id,))
    harness.response = response(b"Corrected source text")
    current = (await harness.acquire(previous=previous)).document
    current_snapshot = freeze_selected_original(current, (current.passages[0].id,))
    assert current.sha256 != previous.sha256
    assert current.previous_sha256 == previous.sha256
    assert frozen_original_from_dict(previous_snapshot).sha256 == previous.sha256
    assert frozen_original_from_dict(current_snapshot).sha256 == current.sha256


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("document", "source_id"), "different-source"),
        (("document", "sha256"), "0" * 64),
        (("document", "owner_id"), "not-a-uuid"),
        (("document", "canonical_url"), "https://127.0.0.1/private"),
        (("document", "byte_count"), True),
        (("document", "expires_at"), "2026-09-14T09:00:00+00:00"),
        (("document", "passages", 0, "text"), "Forged passage"),
        (("document", "passages", 0, "start"), True),
        (("document", "passages", 0, "content_kind"), "translated_derivative"),
    ],
)
async def test_frozen_metadata_or_passage_tampering_is_rejected(path, value):
    harness = Harness()
    document = (await harness.acquire()).document
    frozen = freeze_selected_original(document, (document.passages[0].id,))
    altered = deepcopy(frozen)
    cursor = altered
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    with pytest.raises(ValueError):
        frozen_original_from_dict(altered)


async def test_selection_requires_exact_unique_acquired_passage_ids():
    harness = Harness()
    document = (await harness.acquire()).document
    selected = document.passages[0].id
    for ids in ((), (selected, selected), ("model-invented-passage",)):
        with pytest.raises(ValueError):
            freeze_selected_original(document, ids)


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(schema_version=2),
        lambda value: value["document"].pop("owner_id"),
        lambda value: value["document"].update(unexpected="field"),
        lambda value: value["document"].update(retrieved_at="2026-09-14T10:00:00"),
        lambda value: value["document"].update(requirement_ids=["invalid requirement"]),
        lambda value: value["document"].update(passages=[{"text": "partial"}]),
    ],
)
async def test_version_shape_dates_and_requirements_are_strict(change):
    harness = Harness()
    document = (await harness.acquire()).document
    snapshot = freeze_selected_original(document, (document.passages[0].id,))
    changed = deepcopy(snapshot)
    change(changed)
    with pytest.raises(ValueError):
        frozen_original_from_dict(changed)


def test_non_snapshot_value_is_rejected():
    with pytest.raises(ValueError, match="snapshot"):
        frozen_original_from_dict({"document": {}})

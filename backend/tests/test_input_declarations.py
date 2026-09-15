# ruff: noqa: RUF001
"""Private declarations resolve calendar values and preserve exact frozen citation anchors."""

import json
from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from ase.adapters.research_inputs.memory import MAX_USER_SLOTS
from ase.application.reports.export_text import evidence_metadata
from ase.application.reports.prompts import evidence_block
from ase.domain.errors import InvalidRequest, NotFound, RateLimited
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_matches_time
from ase.domain.input_declarations import InputPassageDeclaration, InputSourceDate
from ase.domain.report_records import evidence_from_list, evidence_to_list
from ase.domain.text_transformations import TextTransformation
from research_input_helpers import Harness
from test_research_input_api import upload_app

TEXT = "شركت می\u200cرود 國家 ۱۴۰۴-۰۱-۰۱"


def declaration(event):
    return InputPassageDeclaration(
        event.id,
        event.content_hash,
        (
            TextTransformation(
                "summary",
                TEXT,
                "Shirkat report 1404-01-01",
                "transliteration",
                "fa",
                "en",
                "operator",
                "Operator transcription v1",
                "Arab",
                "Latn",
            ),
        ),
        (InputSourceDate("summary", "۱۴۰۴-۰۱-۰۱", "publication", "solar_hijri_icu33"),),
    )


async def test_declaration_derives_immutable_private_input_and_frozen_json():
    h = Harness()
    original = await h.service.execute(h.actor, "notes.txt", TEXT.encode())
    before = h.store.read(h.actor, original.id)
    receipt = await h.service.declare(
        h.actor, original.id, original.sha256, (declaration(before.events[0]),)
    )
    result = h.store.read(h.actor, receipt.id)
    assert receipt.parent_input_id == original.id and receipt.sha256 == original.sha256
    assert h.store.read(h.actor, original.id) == before
    event = result.events[0]
    assert event.id == before.events[0].id and event.content_hash == before.events[0].content_hash
    assert event.summary == TEXT and event.published_at == before.events[0].published_at
    assert event.transformations[0].actor_id == h.actor.id
    assert event.source_dates[0].day_start.isoformat() == "2025-03-21"
    frozen = EvidenceItem.from_event(
        "E1", event, h.clock.now(), source_name="Private input", independence_key="private"
    )
    assert "2025-03-21" in evidence_block(frozen)
    assert "transliteration" in evidence_block(frozen)
    assert "timezone unknown" in evidence_block(frozen)
    assert any("2025-03-21" in line for line in evidence_metadata(frozen))
    rows = json.loads(json.dumps(evidence_to_list((frozen,))))
    assert evidence_from_list(rows) == (frozen,)
    assert rows[0]["summary"] == TEXT and rows[0]["transformations"][0]["original_text"] == TEXT
    legacy = replace(frozen, transformations=(), source_dates=())
    assert "transformations" not in evidence_to_list((legacy,))[0]
    assert "source_dates" not in evidence_to_list((legacy,))[0]
    with pytest.raises(InvalidRequest):
        await h.service.declare(h.actor, receipt.id, receipt.sha256, (declaration(event),))
    # Derived inputs occupy the owner's bounded slots; once full, another declaration is refused.
    for index in range(MAX_USER_SLOTS - 2):
        h.store.reserve(h.actor, f"held-{index}.txt")
    with pytest.raises(RateLimited):
        await h.service.declare(
            h.actor, original.id, original.sha256, (declaration(before.events[0]),)
        )


@pytest.mark.parametrize("defect", ["foreign", "digest", "event", "text", "raw", "expiry"])
async def test_declaration_rejects_mismatched_or_expired_anchors(defect):
    h = Harness()
    original = await h.service.execute(h.actor, "notes.txt", TEXT.encode())
    event = h.store.read(h.actor, original.id).events[0]
    row = declaration(event)
    digest = original.sha256
    if defect == "digest":
        digest = "0" * 64
    elif defect == "event":
        row = replace(row, event_id="missing")
    elif defect == "text":
        row = replace(
            row, transformations=(replace(row.transformations[0], original_text="different"),)
        )
    elif defect == "raw":
        row = replace(row, source_dates=(replace(row.source_dates[0], raw_text="1404-01-01"),))
    elif defect == "foreign":
        with pytest.raises(NotFound):
            h.store.read(replace(h.actor, id=uuid4()), original.id)
        return
    else:
        h.clock.advance(timedelta(minutes=16))
    with pytest.raises((InvalidRequest, NotFound)):
        await h.service.declare(h.actor, original.id, digest, (row,))


async def test_api_targets_and_conversion_receipt_without_parser_rerun():
    h = Harness()
    original = await h.service.execute(h.actor, "notes.txt", TEXT.encode())
    async with AsyncClient(
        transport=ASGITransport(app=upload_app(h)), base_url="http://test"
    ) as client:
        target = await client.get(f"/api/research/inputs/{original.id}/declaration-targets")
        assert target.status_code == 200
        row = target.json()["targets"][0]
        payload = {
            "sha256": original.sha256,
            "declarations": [
                {
                    "event_id": row["event_id"],
                    "content_hash": row["content_hash"],
                    "source_dates": [
                        {
                            "field": "summary",
                            "raw_text": "۱۴۰۴-۰۱-۰۱",
                            "role": "publication",
                            "calendar": "solar_hijri_icu33",
                        }
                    ],
                }
            ],
        }
        response = await client.post(
            f"/api/research/inputs/{original.id}/declarations", json=payload
        )
        assert response.status_code == 201, response.text
        derived = await client.get(
            f"/api/research/inputs/{response.json()['id']}/declaration-targets"
        )
        assert derived.json()["targets"][0]["source_dates"][0]["day_start"] == "2025-03-21"
        assert h.extractor.calls == 1


async def test_explicit_publication_instant_qualifies_without_inventing_upload_recency():
    h = Harness()
    raw = "2026-09-06T10:00:00+00:00"
    receipt = await h.service.execute(h.actor, "dated.txt", raw.encode())
    event = h.store.read(h.actor, receipt.id).events[0]
    since, until = h.clock.now() - timedelta(days=1), h.clock.now()
    assert not evidence_matches_time(event, EvidenceTimeBasis.PUBLICATION, since, until)
    row = InputPassageDeclaration(
        event.id,
        event.content_hash,
        source_dates=(InputSourceDate("summary", raw, "publication", "gregorian"),),
    )
    derived = await h.service.declare(h.actor, receipt.id, receipt.sha256, (row,))
    annotated = h.store.read(h.actor, derived.id).events[0]
    assert evidence_matches_time(annotated, EvidenceTimeBasis.PUBLICATION, since, until)
    assert annotated.source_dates[0].basis == "operator"
    assert (
        annotated.observed_at == event.observed_at and annotated.content_hash == event.content_hash
    )

"""The evidence pack, the model contract and the checks run before a digest is stored."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.adapters.security.cipher import FernetCipher
from ase.application.ports.llm import LlmGatewayError
from ase.application.ukraine_digest_evidence import evidence_pack
from ase.application.ukraine_digest_model import SYSTEM_PROMPT, digest_request, digest_schema
from ase.application.ukraine_digest_validation import validate_digest
from ase.application.ukraine_digest_writer import DigestRejected, DigestWriter, cited
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.ukraine.confirmed import (
    CivilianHarm,
    CivilianHarmMonth,
    ConfirmedLosses,
    LossRow,
    loss_group,
)
from ase.domain.ukraine.control import (
    ControlChange,
    ControlSnapshot,
    ControlStatus,
    SettlementControl,
)
from ase.domain.ukraine.digest import UkraineDigest
from ase.domain.ukraine.reference import Side
from helpers import FakeClock
from ukraine_digest_helpers import (
    CLAIM,
    NOW,
    PERIOD_END,
    PERIOD_START,
    answer,
    board,
    result,
)

SECRET = "fixture-digest-secret"
SETTLEMENT = SettlementControl(
    geoname_id=1,
    name="Somewhere",
    oblast="Donetska",
    lat=48.0,
    lon=37.8,
    status=ControlStatus.RU,
    since=None,
    votes=(ControlStatus.RU, ControlStatus.RU, ControlStatus.RU, ControlStatus.UNKNOWN),
)


def snapshot(assessed: date, changes: tuple[ControlChange, ...]) -> ControlSnapshot:
    return ControlSnapshot(
        assessment_date=assessed,
        release_stamp="v1",
        retrieved_at=NOW,
        attribution="VIINA",
        licence="CC-BY",
        source_url="https://example.invalid/control",
        method_note="Majority vote of public maps.",
        places_total=1,
        settlements=(SETTLEMENT,),
        areas=(),
        oblasts=(),
        changes=changes,
    )


@pytest.fixture
def profile() -> LlmProfile:
    cipher = FernetCipher("a" * 32)
    return LlmProfile(
        id=uuid4(),
        name="Digest fixture",
        base_url="https://model.example/v1",
        model="fixture",
        api_key_encrypted=cipher.encrypt(SECRET),
        api_key_hint="cret",
        roles=frozenset({LlmRole.ASSESSMENT}),
        max_output_tokens=4000,
        temperature=0.1,
        enabled=True,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def writer() -> tuple[AsyncMock, AsyncMock, DigestWriter]:
    gateway, record = AsyncMock(), AsyncMock()
    return gateway, record, DigestWriter(gateway, FernetCipher("a" * 32), FakeClock(NOW), record)


def digest_of(text: str = answer()) -> UkraineDigest:
    return UkraineDigest.model_validate_json(text)


def test_pack_covers_every_collected_strand_and_says_plainly_what_is_missing() -> None:
    pack = evidence_pack(board(), NOW)
    kinds = {item.kind for item in pack.items}
    assert kinds == {"assessment", "battlefield", "political", "claim"}
    assert (pack.period_start, pack.period_end) == (PERIOD_START, PERIOD_END)
    assert [item.id for item in pack.items] == [f"e{n}" for n in range(1, len(pack.items) + 1)]
    claim = next(item for item in pack.items if item.kind == "claim")
    assert "one side's claims, not verified counts" in claim.detail
    joined = " ".join(pack.notes)
    assert "No control map snapshot has been imported" in joined
    assert "No visually confirmed loss import is available." in joined
    assert "No United Nations civilian casualty import is available." in joined
    assert "isw_assessments" in pack.source_ids and "kyiv_independent" in pack.source_ids


def test_pack_is_bounded_trimmed_and_dated_inside_the_fortnight() -> None:
    long_board = board(
        updates=tuple(
            replace(
                entry,
                event=entry.event.with_changes(
                    id=f"{entry.event.id}-{index}", title="T" * 400, summary="S" * 900
                ),
            )
            for index in range(12)
            for entry in board().updates
        )
    )
    pack = evidence_pack(long_board, NOW)
    assert len(pack.items) <= 40
    assert all(len(item.label) <= 180 and len(item.detail) <= 420 for item in pack.items)
    assert all(
        item.dated_on is None or PERIOD_START <= item.dated_on <= PERIOD_END for item in pack.items
    )


def test_pack_reports_control_change_losses_and_civilian_harm_when_imported() -> None:
    control = snapshot(
        PERIOD_END,
        (
            ControlChange(
                geoname_id=1,
                name="Somewhere",
                oblast="Donetska",
                previous=ControlStatus.UA,
                status=ControlStatus.RU,
                changed_on=PERIOD_END - timedelta(days=2),
            ),
        ),
    )
    losses = ConfirmedLosses(
        recorded_on=PERIOD_END,
        retrieved_at=NOW,
        attribution="Oryx",
        licence="CC-BY",
        source_url="https://example.invalid/oryx",
        rows=(
            LossRow(Side.RU, "All Types", loss_group("All Types"), 10, 2, 1, 3),
            LossRow(Side.UA, "All Types", loss_group("All Types"), 4, 1, 0, 1),
        ),
        days=(),
    )
    harm = CivilianHarm(
        retrieved_at=NOW,
        source_url="https://example.invalid/hrmmu",
        attribution="OHCHR",
        months=(
            CivilianHarmMonth(
                month=date(2026, 8, 1),
                title="August",
                url="https://example.invalid/august",
                published_on=PERIOD_END - timedelta(days=3),
                killed=120,
                injured=530,
            ),
        ),
        references=(),
    )
    pack = evidence_pack(board(control=control, confirmed=losses, civilian_harm=harm), NOW)
    kinds = [item.kind for item in pack.items]
    assert kinds.count("losses") == 2 and "control" in kinds and "civilian" in kinds
    control = next(item for item in pack.items if item.kind == "control")
    assert "not observed positions" in control.detail
    assert "considerably higher" in next(i for i in pack.items if i.kind == "civilian").detail


def test_pack_states_plainly_when_the_control_snapshot_records_no_change_in_the_fortnight() -> None:
    pack = evidence_pack(board(control=snapshot(PERIOD_START - timedelta(days=40), ())), NOW)
    assert any("records no settlement change inside" in note for note in pack.notes)


def test_pack_notes_when_no_assessment_or_claim_was_collected() -> None:
    pack = evidence_pack(
        board(updates=tuple(e for e in board().updates if e.event.source_id != "isw_assessments")),
        NOW,
    )
    joined = " ".join(pack.notes)
    assert "No Institute for the Study of War assessment" in joined
    stale = replace(CLAIM, reported_on=PERIOD_START - timedelta(days=3))
    assert "No General Staff of Ukraine daily claim" in " ".join(
        evidence_pack(board(claims=(stale,)), NOW).notes
    )


def test_prompt_and_schema_bound_the_single_call(profile: LlmProfile) -> None:
    pack = evidence_pack(board(), NOW)
    request = digest_request(profile, pack)
    assert request.schema_name == "ukraine_digest"
    assert request.max_output_tokens == 3_000
    assert request.messages[0].content == SYSTEM_PROMPT
    assert json.loads(request.messages[1].content)["period"]["to"] == PERIOD_END.isoformat()
    assert len(request.messages) == 2
    for rule in ("UK English", "untrusted evidence", "never as", "Do not write any URL"):
        assert rule in SYSTEM_PROMPT
    schema = digest_schema()
    assert "$defs" not in json.dumps(schema) and "$ref" not in json.dumps(schema)
    assert set(schema["properties"]) == {
        "period",
        "battlefield",
        "political",
        "watch",
        "caveats",
    }
    assert schema["properties"]["period"]["properties"].keys() == {"from", "to"}


def test_corrections_are_appended_for_the_single_retry(profile: LlmProfile) -> None:
    pack = evidence_pack(board(), NOW)
    request = digest_request(profile, pack, ("e99 is not in the pack",))
    assert len(request.messages) == 3
    assert "e99 is not in the pack" in request.messages[2].content


def test_an_empty_pack_is_never_sent(profile: LlmProfile) -> None:
    empty = board(updates=(), claims=())
    with pytest.raises(ValueError, match="at least one piece of evidence"):
        digest_request(profile, evidence_pack(empty, NOW))


def test_bounds_reject_too_few_changes_and_over_long_text() -> None:
    payload = json.loads(answer())
    payload["battlefield"]["changes"] = payload["battlefield"]["changes"][:1]
    with pytest.raises(ValueError):
        UkraineDigest.model_validate(payload)
    payload = json.loads(answer())
    payload["watch"][0] = "x" * 400
    with pytest.raises(ValueError):
        UkraineDigest.model_validate(payload)


def test_a_well_formed_answer_passes_every_check() -> None:
    pack = evidence_pack(board(), NOW)
    assert validate_digest(digest_of(), pack) == ()
    assert [item.id for item in cited(digest_of(), pack)] == ["e1", "e3", "e6", "e7"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Reporting suggests 4321 vehicles were destroyed near the city.", "do not appear"),
        (
            "Reporting suggests fighting continued on 2026-07-04 near the city.",
            "outside the period",
        ),
        ("Reporting suggests fighting continued, see https://invented.example/x now.", "links"),
        ("Reporting suggests fighting continued — without confirmed change.", "em dashes"),
    ],
)
def test_invented_numbers_dates_links_and_em_dashes_are_rejected(text: str, expected: str) -> None:
    errors = validate_digest(digest_of(answer(battlefield_text=text)), evidence_pack(board(), NOW))
    assert any(expected in error for error in errors)


def test_unknown_or_repeated_evidence_ids_and_a_wrong_period_are_rejected() -> None:
    pack = evidence_pack(board(), NOW)
    assert any(
        "not in the pack" in e for e in validate_digest(digest_of(answer(ids=("e99",))), pack)
    )
    assert any("repeated" in e for e in validate_digest(digest_of(answer(ids=("e1", "e1"))), pack))
    shifted = answer(starts_on=PERIOD_START - timedelta(days=1))
    assert any("restated exactly" in e for e in validate_digest(digest_of(shifted), pack))


def test_numbers_copied_from_the_pack_are_accepted() -> None:
    pack = evidence_pack(board(), NOW)
    claim = next(item for item in pack.items if item.kind == "claim")
    assert "1000000" in claim.detail.replace(",", "")
    text = (
        "The General Staff of Ukraine claimed a cumulative total of 1000000 Russian personnel, "
        "which is a claim rather than a verified count."
    )
    assert validate_digest(digest_of(answer(battlefield_text=text)), pack) == ()


async def test_a_rejected_answer_is_retried_once_with_the_errors_then_stored_nowhere(
    profile: LlmProfile, writer: tuple[AsyncMock, AsyncMock, DigestWriter]
) -> None:
    gateway, record, service = writer
    bad = answer(battlefield_text="Reporting suggests 4321 vehicles were lost near the city.")
    gateway.complete.return_value = result(bad)
    pack = evidence_pack(board(), NOW)
    with pytest.raises(DigestRejected) as rejected:
        await service.write(profile, pack)
    assert gateway.complete.await_count == 2
    second = gateway.complete.await_args_list[1].args[3]
    assert "do not appear in the pack" in second.messages[2].content
    assert any("4321" in error for error in rejected.value.errors)
    assert record.await_count == 2 and record.await_args.args[0].purpose == "ukraine_digest"


async def test_a_second_attempt_that_passes_is_accepted(
    profile: LlmProfile, writer: tuple[AsyncMock, AsyncMock, DigestWriter]
) -> None:
    gateway, _record, service = writer
    gateway.complete.side_effect = [
        result(answer(ids=("e99",))),
        result(answer()),
    ]
    written = await service.write(profile, evidence_pack(board(), NOW))
    assert written.model == "fixture-model"
    assert (written.prompt_tokens, written.completion_tokens) == (900, 300)


@pytest.mark.parametrize(
    ("content", "expected"),
    [("not json at all", "invalid response"), ("x" * 30_000, "invalid response")],
)
async def test_unusable_model_output_fails_without_storing_and_records_the_call(
    profile: LlmProfile,
    writer: tuple[AsyncMock, AsyncMock, DigestWriter],
    content: str,
    expected: str,
) -> None:
    gateway, record, service = writer
    gateway.complete.return_value = result(content)
    with pytest.raises(LlmGatewayError, match=expected):
        await service.write(profile, evidence_pack(board(), NOW))
    assert record.await_args.args[0].ok is False


async def test_the_api_key_never_leaves_the_cipher_and_a_broken_cipher_is_not_echoed(
    profile: LlmProfile, writer: tuple[AsyncMock, AsyncMock, DigestWriter]
) -> None:
    gateway, _record, service = writer
    gateway.complete.return_value = result(answer())
    await service.write(profile, evidence_pack(board(), NOW))
    assert gateway.complete.await_args.args[1] == SECRET
    broken = DigestWriter(gateway, FernetCipher(None), FakeClock(NOW), AsyncMock())
    with pytest.raises(LlmGatewayError) as error:
        await broken.write(profile, evidence_pack(board(), NOW))
    assert SECRET not in str(error.value)

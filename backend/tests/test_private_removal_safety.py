"""Removal refuses uncertainty, foreign authorship, stale authority and incomplete inventories."""

import json
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from ase.adapters.persistence.assistant_history import SqlAssistantHistory
from ase.adapters.persistence.assistant_history_models import AssistantConversationRow
from ase.adapters.persistence.claim_models import ClaimRevisionRow, ClaimRow
from ase.adapters.persistence.models import IndicatorRow, ReportRow, UserRow
from ase.adapters.persistence.private_removal import SqlPrivateRemovalRepository
from ase.adapters.persistence.private_removal_authorship import authorship_blocker
from ase.adapters.persistence.report_job_codec import payload_columns
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.research_usage import SqlResearchUsageRepository
from ase.adapters.persistence.warning_consumption_models import WarningConsumptionRow
from ase.application.research.phase_ledger import (
    abandon_operation,
    reserve_operation,
    settle_operation,
)
from ase.domain.errors import Conflict, Forbidden, InvalidRequest
from ase.domain.private_removal import RemovalRequest, RemovalScope, ReviewDecision, ReviewPurpose
from ase.domain.research import ResearchMode
from private_removal_helpers import apply, authorise, preview, report
from report_job_helpers import job


@pytest.mark.parametrize(
    "payload",
    [
        {"calls": [{"status": "uncertain", "completion_tokens": 0}]},
        {"calls": [{"status": "completed", "completion_tokens": None}]},
        {"calls": "corrupt"},
        {"source_phase_ledger": {"mode": "quick"}},
    ],
)
async def test_uncertain_or_malformed_checkpoint_is_retained(container, user, admin, payload):
    await authorise(container, admin, user)
    checkpoint = job(owner_id=user.id, status="paused")
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(checkpoint)
        await session.execute(
            update(ReportJobRow)
            .where(ReportJobRow.id == checkpoint.id)
            .values(**payload_columns({"schema_version": 1, **payload}))
        )
        await session.commit()
    plan = await preview(container, admin, RemovalRequest(user.id, RemovalScope.JOB, checkpoint.id))
    assert "active_uncertain_or_unverifiable_job" in plan.blockers


@pytest.mark.parametrize("state", ["open", "unknown", "settled"])
async def test_source_operation_receipts_survive_until_fully_settled(container, user, admin, state):
    await authorise(container, admin, user)
    payload = {"schema_version": 1}
    reserve_operation(payload, mode=ResearchMode.QUICK, phase="initial", request_key="source:1")
    if state == "unknown":
        abandon_operation(payload, mode=ResearchMode.QUICK, phase="initial", request_key="source:1")
    elif state == "settled":
        settle_operation(
            payload,
            mode=ResearchMode.QUICK,
            phase="initial",
            request_key="source:1",
            elapsed_ms=100,
            retained_item_keys=("public:1",),
        )
    checkpoint = job(owner_id=user.id, status="paused", payload=payload)
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(checkpoint)
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.JOB, checkpoint.id)
    plan = await preview(container, admin, request)
    if state != "settled":
        assert "active_uncertain_or_unverifiable_job" in plan.blockers
        with pytest.raises(Conflict, match="blocked"):
            await apply(container, admin, request, plan.fingerprint)
    else:
        assert not plan.blockers
        await apply(container, admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        retained = await SqlReportJobRepository(session).get(checkpoint.id)
        assert (retained is not None) == (state != "settled")
        if retained is not None:
            assert retained.payload == payload


async def test_failed_audit_rolls_back_every_deletion(container, user, admin, monkeypatch):
    await authorise(container, admin, user)
    target, _ = await report(container, user)
    request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
    plan = await preview(container, admin, request)
    async with container.session_factory() as session:
        service = container.private_removal(session)

        async def unavailable(*args, **kwargs):
            raise RuntimeError("Synthetic audit failure")

        monkeypatch.setattr(service.auditor, "record", unavailable)
        with pytest.raises(RuntimeError, match="Synthetic"):
            await service.apply(admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        assert await session.get(ReportRow, target.id) is not None


@pytest.mark.parametrize(
    "module,setting",
    [
        ("private_removal_selection", "MAX_ROWS"),
        ("private_removal_selection", "MAX_BYTES"),
        ("private_removal_references", "MAX_REFERENCE_ROWS"),
        ("private_removal_references", "MAX_REFERENCE_BYTES"),
    ],
)
async def test_incomplete_inventory_never_permits_removal(
    container, user, admin, monkeypatch, module, setting
):
    await authorise(container, admin, user)
    target, _ = await report(container, user)
    await report(container, admin)
    monkeypatch.setattr(f"ase.adapters.persistence.{module}.{setting}", 0)
    request = RemovalRequest(user.id, RemovalScope.REPORT, target.id)
    plan = await preview(container, admin, request)
    assert any("inventory" in code for code in plan.blockers)
    with pytest.raises(Conflict, match="blocked"):
        await apply(container, admin, request, plan.fingerprint)


async def test_other_persons_authored_claim_revision_is_preserved(container, user, admin):
    await authorise(container, admin, user)
    target, version = await report(container, user)
    claim_id, revision_id = uuid4(), uuid4()
    async with container.session_factory() as session:
        session.add(
            ClaimRow(
                id=claim_id,
                report_id=target.id,
                report_version_id=version.id,
                created_by=user.id,
                team_id=None,
                evidence_sha256="a" * 64,
                latest_revision_id=revision_id,
                created_at=container.clock.now(),
            )
        )
        await session.flush()
        session.add(
            ClaimRevisionRow(
                id=revision_id,
                claim_id=claim_id,
                number=1,
                payload={"authored_by": str(admin.id)},
                content_sha256="b" * 64,
                byte_size=64,
            )
        )
        await session.commit()
    plan = await preview(container, admin, RemovalRequest(user.id, RemovalScope.REPORT, target.id))
    assert "other_person_authored_revision" in plan.blockers


@pytest.mark.parametrize(
    "name,payload,extra",
    [
        ("claim_revisions", {}, {}),
        ("identity_decision_revisions", {"authored_by": "invalid"}, {}),
        ("relationship_review_revisions", {"authored_by": None}, {}),
        ("source_review_revisions", "bad-json", {}),
        ("source_review_snapshots", "[]", {}),
        ("report_ledger_entries", {"method": "unexpected"}, {"entry_kind": "forecast_decision"}),
    ],
)
def test_unverifiable_authorship_is_never_assumed_to_belong_to_owner(name, payload, extra):
    assert (
        authorship_blocker(name, {"payload": payload, **extra}, uuid4())
        == "unverifiable_revision_authorship"
    )


@pytest.mark.parametrize(
    "name,path",
    [
        ("claim_revisions", "authored_by"),
        ("source_review_revisions", "assessor_id"),
        ("report_ledger_entries", "actor_id"),
    ],
)
def test_verified_authors_and_non_person_ledger_receipts(name, path):
    owner = uuid4()
    payload = {path: str(owner), "method": "reviewer"}
    if name == "source_review_revisions":
        payload = {"review": payload}
    row = {"payload": json.dumps(payload), "entry_kind": "forecast_decision"}
    assert authorship_blocker(name, row, owner) is None
    assert authorship_blocker(name, row, uuid4()) == "other_person_authored_revision"
    assert (
        authorship_blocker(
            "report_ledger_entries",
            {
                "payload": {"method": "clock", "actor_id": "clock"},
                "entry_kind": "forecast_decision",
            },
            owner,
        )
        is None
    )
    assert (
        authorship_blocker(
            "report_ledger_entries", {"payload": {}, "entry_kind": "indicator_version"}, owner
        )
        is None
    )


@pytest.mark.parametrize("linked", [True, False])
async def test_saved_chat_exact_report_reference_blocks_removal(container, user, admin, linked):
    await authorise(container, admin, user)
    target, _ = await report(container, user)
    turn = {"question": str(target.id), "answer": {}}
    if linked:
        turn["report"] = {"id": str(target.id), "version": 1}
    async with container.session_factory() as session:
        await SqlAssistantHistory(session).create(user.id, "Notes", [turn], container.clock.now())
        await session.commit()
    plan = await preview(container, admin, RemovalRequest(user.id, RemovalScope.REPORT, target.id))
    assert ("retained_structured_reference" in plan.blockers) == linked


async def test_removed_account_cannot_recreate_transcripts_or_tier(container, user, admin):
    await authorise(container, admin, user, inactive=True)
    request = RemovalRequest(user.id, RemovalScope.ACCOUNT)
    await apply(container, admin, request, (await preview(container, admin, request)).fingerprint)
    async with container.session_factory() as session:
        with pytest.raises(Forbidden):
            await SqlAssistantHistory(session).create(user.id, "Stale", [], container.clock.now())
        with pytest.raises(Conflict, match="removed"):
            await SqlResearchUsageRepository(session).assign(user.id, 2, 1)
        assert await session.scalar(select(AssistantConversationRow)) is None


async def test_evaluated_private_indicator_is_removed_with_consumption(container, user, admin):
    await authorise(container, admin, user, inactive=True)
    now = container.clock.now()
    rule = uuid4()
    async with container.session_factory() as session:
        session.add(
            IndicatorRow(
                id=rule,
                team_id=None,
                name="Private warning",
                description="",
                plan_id=None,
                countries=[],
                categories=[],
                keywords=[],
                created_by=user.id,
                created_at=now,
                updated_at=now,
                enabled=False,
            )
        )
        await session.flush()
        session.add(WarningConsumptionRow(indicator_id=rule, data=b"ASEC\x01", count=0))
        await session.commit()
    request = RemovalRequest(user.id, RemovalScope.ACCOUNT)
    plan = await preview(container, admin, request)
    assert not plan.blockers
    assert plan.counts["warning_consumption"] == 1
    await apply(container, admin, request, plan.fingerprint)
    async with container.session_factory() as session:
        assert await session.get(WarningConsumptionRow, rule) is None
        assert await session.get(IndicatorRow, rule) is None


async def test_fresh_admin_authority_and_explicit_review_arguments(container, user, admin):
    await authorise(container, admin, user)
    async with container.session_factory() as session:
        with pytest.raises(Conflict, match="fresh"):
            await SqlPrivateRemovalRepository(session).remove(
                RemovalRequest(user.id, RemovalScope.ACCOUNT), container.clock.now()
            )
        for days, revision in ((0, 0), (91, 0), (1, -1)):
            with pytest.raises(InvalidRequest):
                await container.private_removal(session).review(
                    admin,
                    user.id,
                    ReviewDecision.HOLD,
                    ReviewPurpose.QUARTERLY,
                    revision,
                    days=days,
                )
        await session.execute(update(UserRow).where(UserRow.id == admin.id).values(role="user"))
        await session.commit()
    with pytest.raises(Forbidden):
        await preview(container, admin, RemovalRequest(user.id, RemovalScope.ACCOUNT))

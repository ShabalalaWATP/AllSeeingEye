"""Scoped immutable identity storage, conditional correction and transaction ownership."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.identity_decisions import SqlIdentityDecisionRepository
from ase.adapters.persistence.identity_models import IdentityDecisionRow, IdentityRevisionRow
from ase.domain.access import Visibility
from ase.domain.identity_review import IdentityDisposition, revise_identity_decision
from report_documents_helpers import document_records
from test_identity_review import arguments


async def seeded(container, user):
    args = arguments()
    record, _ = document_records(user.id)
    record.id = args["version"].report_id
    revision = revise_identity_decision(**args)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, args["version"])
        await SqlIdentityDecisionRepository(session).create(revision, "a" * 64)
        await session.commit()
    return record, args, revision


async def test_roundtrip_owner_scope_and_stale_correction(container, user):
    record, args, first = await seeded(container, user)
    second = revise_identity_decision(
        **{
            **args,
            "previous": first,
            "revision_id": uuid4(),
            "disposition": IdentityDisposition.REJECTED,
        }
    )
    async with container.session_factory() as session:
        repo = SqlIdentityDecisionRepository(session)
        root = await repo.get(first.decision_id)
        assert root.created_by == user.id != first.authored_by
        assert root.report_id == record.id and root.subject == first.subject
        assert root.candidate_label == "E1" and root.evidence_sha256 == "a" * 64
        assert await repo.append(second, first.id)
        await session.commit()
        assert not await repo.append(replace(second, id=uuid4()), first.id)
        assert await repo.revision(first.decision_id, first.id) == first
        assert await repo.revision(first.decision_id, second.id) == second
        assert await repo.revision(uuid4(), second.id) is None
        assert (await repo.get(first.decision_id)).latest_revision_id == second.id
        count, size = await repo.scope_usage(user.id, None)
        assert count == 1 and size == repo.storage_size(first) + repo.storage_size(second)


async def test_changed_subject_cannot_be_appended_directly(container, user):
    _, _, first = await seeded(container, user)
    changed = replace(first, id=uuid4(), previous_id=first.id, number=2, subject="Another company")
    async with container.session_factory() as session:
        with pytest.raises(ValueError):
            await SqlIdentityDecisionRepository(session).append(changed, first.id)


async def test_duplicate_candidate_in_version_is_rejected(container, user):
    _, _, first = await seeded(container, user)
    async with container.session_factory() as session:
        with pytest.raises(IntegrityError):
            await SqlIdentityDecisionRepository(session).create(
                replace(first, id=uuid4(), decision_id=uuid4()), "a" * 64
            )
        await session.rollback()
        assert await session.scalar(select(func.count()).select_from(IdentityDecisionRow)) == 1
        assert await session.scalar(select(func.count()).select_from(IdentityRevisionRow)) == 1


async def test_caller_rollback_preserves_history_and_explicit_delete_clears_children(
    container, user
):
    record, _, first = await seeded(container, user)
    second = replace(first, id=uuid4(), number=2, previous_id=first.id)
    async with container.session_factory() as session:
        repo = SqlIdentityDecisionRepository(session)
        assert await repo.append(second, first.id)
        await session.rollback()
        assert (await repo.get(first.decision_id)).latest_revision_id == first.id
        assert await repo.revision(first.decision_id, second.id) is None
        await repo.delete_for_report(record.id)
        await session.commit()
        assert await session.scalar(select(func.count()).select_from(IdentityDecisionRow)) == 0
        assert await session.scalar(select(func.count()).select_from(IdentityRevisionRow)) == 0


async def test_visibility_is_applied_before_counts_and_pagination(container, user):
    record, args, first = await seeded(container, user)
    async with container.session_factory() as session:
        repo = SqlIdentityDecisionRepository(session)
        version_id = args["version"].id
        assert await repo.list_ids(Visibility(uuid4(), False, ()), record.id, version_id, 1, 0) == (
            (),
            0,
        )
        assert await repo.list_ids(Visibility(user.id, False, ()), record.id, version_id, 1, 0) == (
            (first.decision_id,),
            1,
        )
        assert await repo.list_ids(Visibility(user.id, False, ()), record.id, version_id, 1, 1) == (
            (),
            1,
        )
        assert await repo.list_ids(Visibility(uuid4(), True, ()), record.id, version_id, 1, 0) == (
            (first.decision_id,),
            1,
        )


async def test_failed_revision_insert_rolls_back_successful_pointer_update(container, user):
    _, _, first = await seeded(container, user)
    _, _, other = await seeded(container, user)
    duplicate = replace(first, id=other.id, number=2, previous_id=first.id)
    async with container.session_factory() as session:
        repo = SqlIdentityDecisionRepository(session)
        before = await repo.scope_usage(user.id, None)
        with pytest.raises(IntegrityError):
            await repo.append(duplicate, first.id)
        await session.rollback()
        assert (await repo.get(first.decision_id)).latest_revision_id == first.id
        assert await repo.revision(first.decision_id, other.id) is None
        assert await repo.revision(first.decision_id, first.id) == first
        assert await repo.scope_usage(user.id, None) == before


async def test_report_deletion_removes_only_its_reviews_and_can_roll_back(container, user):
    record, _, first = await seeded(container, user)
    other_record, _, other = await seeded(container, user)
    async with container.session_factory() as session:
        if session.get_bind().dialect.name == "sqlite":
            await session.execute(text("PRAGMA foreign_keys=ON"))
            assert await session.scalar(text("PRAGMA foreign_keys")) == 1
        reports = container.repositories(session).reports
        identities = SqlIdentityDecisionRepository(session)
        await reports.delete(record.id)
        assert await identities.get(first.decision_id) is None
        assert await identities.revision(first.decision_id, first.id) is None
        await session.rollback()
        assert await identities.revision(first.decision_id, first.id) == first
        await reports.delete(record.id)
        await session.commit()
        assert await identities.get(first.decision_id) is None
        assert await identities.revision(first.decision_id, first.id) is None
        assert (await identities.get(other.decision_id)).report_id == other_record.id
        assert await identities.revision(other.decision_id, other.id) == other


async def test_revision_index_corruption_is_rejected(container, user):
    _, _, first = await seeded(container, user)
    async with container.session_factory() as session:
        await session.execute(
            update(IdentityRevisionRow).where(IdentityRevisionRow.id == first.id).values(number=2)
        )
        with pytest.raises(ValueError, match="index mismatch"):
            await SqlIdentityDecisionRepository(session).revision(first.decision_id, first.id)
        await session.rollback()


async def test_creation_rejects_a_version_from_another_report(container, user):
    _, _, first = await seeded(container, user)
    _, _, other = await seeded(container, user)
    invalid = replace(
        first, id=uuid4(), decision_id=uuid4(), report_version_id=other.report_version_id
    )
    async with container.session_factory() as session:
        repo = SqlIdentityDecisionRepository(session)
        before = await repo.scope_usage(user.id, None)
        with pytest.raises(ValueError, match="exact parent"):
            await repo.create(invalid, "a" * 64)
        assert await repo.get(invalid.decision_id) is None
        assert await repo.scope_usage(user.id, None) == before

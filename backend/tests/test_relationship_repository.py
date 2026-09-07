"""Scoped immutable relationship storage, conditional correction and transaction ownership."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.relationship_models import (
    RelationshipReviewRow,
    RelationshipRevisionRow,
)
from ase.adapters.persistence.relationship_reviews import SqlRelationshipReviewRepository
from ase.domain.access import Visibility
from ase.domain.relationship_review import RelationshipDisposition, revise_relationship_review
from report_documents_helpers import document_records
from test_relationship_review import arguments


async def seeded(container, user):
    args = arguments()
    record, _ = document_records(user.id)
    record.id = args["version"].report_id
    revision = revise_relationship_review(**args)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, args["version"])
        await SqlRelationshipReviewRepository(session).create(revision, "a" * 64)
        await session.commit()
    return record, args, revision


async def test_roundtrip_owner_scope_and_stale_correction(container, user):
    record, args, first = await seeded(container, user)
    second = revise_relationship_review(
        **{
            **args,
            "previous": first,
            "revision_id": uuid4(),
            "disposition": RelationshipDisposition.DISPUTED,
        }
    )
    async with container.session_factory() as session:
        repo = SqlRelationshipReviewRepository(session)
        root = await repo.get(first.relationship_id)
        assert root.created_by == user.id != first.authored_by
        assert root.report_id == record.id
        assert root.evidence_label == "E1" and root.evidence_sha256 == "a" * 64
        assert await repo.append(second, first.id)
        await session.commit()
        assert not await repo.append(replace(second, id=uuid4()), first.id)
        assert await repo.revision(first.relationship_id, first.id) == first
        assert await repo.revision(first.relationship_id, second.id) == second
        assert await repo.revision(uuid4(), second.id) is None
        assert (await repo.get(first.relationship_id)).latest_revision_id == second.id
        count, size = await repo.scope_usage(user.id, None)
        assert count == 1 and size == repo.storage_size(first) + repo.storage_size(second)


async def test_changed_assertion_cannot_be_appended_directly(container, user):
    _, _, first = await seeded(container, user)
    changed = replace(
        first,
        id=uuid4(),
        previous_id=first.id,
        number=2,
        assertion=replace(first.assertion, source_id="changed-source"),
    )
    async with container.session_factory() as session:
        with pytest.raises(ValueError):
            await SqlRelationshipReviewRepository(session).append(changed, first.id)


async def test_duplicate_assertion_in_version_is_rejected(container, user):
    _, _, first = await seeded(container, user)
    async with container.session_factory() as session:
        with pytest.raises(IntegrityError):
            await SqlRelationshipReviewRepository(session).create(
                replace(first, id=uuid4(), relationship_id=uuid4()), "a" * 64
            )
        await session.rollback()
        assert await session.scalar(select(func.count()).select_from(RelationshipReviewRow)) == 1
        assert await session.scalar(select(func.count()).select_from(RelationshipRevisionRow)) == 1


async def test_caller_rollback_preserves_history_and_explicit_delete_clears_children(
    container, user
):
    record, _, first = await seeded(container, user)
    second = replace(first, id=uuid4(), number=2, previous_id=first.id)
    async with container.session_factory() as session:
        repo = SqlRelationshipReviewRepository(session)
        assert await repo.append(second, first.id)
        await session.rollback()
        assert (await repo.get(first.relationship_id)).latest_revision_id == first.id
        assert await repo.revision(first.relationship_id, second.id) is None
        await repo.delete_for_report(record.id)
        await session.commit()
        assert await session.scalar(select(func.count()).select_from(RelationshipReviewRow)) == 0
        assert await session.scalar(select(func.count()).select_from(RelationshipRevisionRow)) == 0


async def test_visibility_is_applied_before_counts_and_pagination(container, user):
    record, args, first = await seeded(container, user)
    async with container.session_factory() as session:
        repo = SqlRelationshipReviewRepository(session)
        version_id = args["version"].id
        assert await repo.list_ids(Visibility(uuid4(), False, ()), record.id, version_id, 1, 0) == (
            (),
            0,
        )
        assert await repo.list_ids(Visibility(user.id, False, ()), record.id, version_id, 1, 0) == (
            (first.relationship_id,),
            1,
        )
        assert await repo.list_ids(Visibility(user.id, False, ()), record.id, version_id, 1, 1) == (
            (),
            1,
        )
        assert await repo.list_ids(Visibility(uuid4(), True, ()), record.id, version_id, 1, 0) == (
            (first.relationship_id,),
            1,
        )


async def test_failed_revision_insert_rolls_back_successful_pointer_update(container, user):
    _, _, first = await seeded(container, user)
    _, _, other = await seeded(container, user)
    duplicate = replace(first, id=other.id, number=2, previous_id=first.id)
    async with container.session_factory() as session:
        repo = SqlRelationshipReviewRepository(session)
        before = await repo.scope_usage(user.id, None)
        with pytest.raises(IntegrityError):
            await repo.append(duplicate, first.id)
        await session.rollback()
        assert (await repo.get(first.relationship_id)).latest_revision_id == first.id
        assert await repo.revision(first.relationship_id, other.id) is None
        assert await repo.revision(first.relationship_id, first.id) == first
        assert await repo.scope_usage(user.id, None) == before


@pytest.mark.parametrize("foreign_keys", [True, False])
async def test_report_deletion_removes_only_its_reviews_and_can_roll_back(
    container, user, foreign_keys
):
    record, _, first = await seeded(container, user)
    other_record, _, other = await seeded(container, user)
    async with container.session_factory() as session:
        if session.get_bind().dialect.name == "sqlite":
            await session.execute(
                text("PRAGMA foreign_keys=ON" if foreign_keys else "PRAGMA foreign_keys=OFF")
            )
            assert await session.scalar(text("PRAGMA foreign_keys")) == int(foreign_keys)
        reports = container.repositories(session).reports
        identities = SqlRelationshipReviewRepository(session)
        await reports.delete(record.id)
        assert await identities.get(first.relationship_id) is None
        assert await identities.revision(first.relationship_id, first.id) is None
        await session.rollback()
        assert await identities.revision(first.relationship_id, first.id) == first
        await reports.delete(record.id)
        await session.commit()
        assert await identities.get(first.relationship_id) is None
        assert await identities.revision(first.relationship_id, first.id) is None
        assert (await identities.get(other.relationship_id)).report_id == other_record.id
        assert await identities.revision(other.relationship_id, other.id) == other


async def test_revision_index_corruption_is_rejected(container, user):
    _, _, first = await seeded(container, user)
    async with container.session_factory() as session:
        await session.execute(
            update(RelationshipRevisionRow)
            .where(RelationshipRevisionRow.id == first.id)
            .values(number=2)
        )
        with pytest.raises(ValueError, match="index mismatch"):
            await SqlRelationshipReviewRepository(session).revision(first.relationship_id, first.id)
        await session.rollback()


async def test_creation_rejects_a_version_from_another_report(container, user):
    _, _, first = await seeded(container, user)
    _, _, other = await seeded(container, user)
    invalid = replace(
        first, id=uuid4(), relationship_id=uuid4(), report_version_id=other.report_version_id
    )
    async with container.session_factory() as session:
        repo = SqlRelationshipReviewRepository(session)
        before = await repo.scope_usage(user.id, None)
        with pytest.raises(ValueError, match="exact parent"):
            await repo.create(invalid, "a" * 64)
        assert await repo.get(invalid.relationship_id) is None
        assert await repo.scope_usage(user.id, None) == before

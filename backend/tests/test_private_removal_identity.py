"""A permanent privacy marker cannot be undone by stale or ordinary account writes."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.persistence.private_review_models import PrivateDataReviewRow
from ase.adapters.persistence.users import SqlUserRepository
from ase.domain.errors import Conflict


async def mark_erased(container, owner, actor):
    now = container.clock.now()
    async with container.session_factory() as session:
        session.add(
            PrivateDataReviewRow(
                owner_id=owner.id,
                revision=1,
                decision="remove",
                purpose="account_closure",
                reviewed_by=actor.id,
                reviewed_at=now,
                next_review_at=now + timedelta(days=90),
                erased_at=now,
            )
        )
        await session.commit()


@pytest.mark.parametrize(
    "changes", [{"is_active": True}, {"display_name": "Restored"}, {"password_hash": "synthetic"}]
)
async def test_erased_identity_rejects_all_repository_saves(container, user, admin, changes):
    stale = replace(user, is_active=False)
    await mark_erased(container, user, admin)
    async with container.session_factory() as session:
        repository = SqlUserRepository(session)
        await repository.lock_by_id(user.id)
        with pytest.raises(Conflict, match="removed"):
            await repository.save(replace(stale, **changes))


async def test_cached_identity_cannot_miss_new_committed_erasure_marker(container, user, admin):
    async with container.session_factory() as session:
        repository = SqlUserRepository(session)
        cached = await repository.get_by_id(user.id)
        await mark_erased(container, user, admin)
        with pytest.raises(Conflict, match="removed"):
            await repository.save(cached)

"""Resolver lookup rejects unavailable capabilities and preserves exact revision scope."""

from dataclasses import replace
from uuid import uuid4

import pytest

from annotation_monitor_helpers import seeded
from ase.application.reports.claim_export_selection import SelectClaimExport
from ase.application.reports.monitor_comparisons import resolve_side
from ase.domain.annotation_monitoring import WatchedRevision
from ase.domain.errors import Conflict, InvalidRequest, NotFound


@pytest.mark.parametrize("kind", ["identity", "relationship"])
async def test_missing_optional_capability_fails_as_controlled_unavailable(
    client, container, user, kind
):
    _, _, _, _, monitor = await seeded(client, container, user)
    monitor = replace(monitor, watches=(WatchedRevision(kind, uuid4(), uuid4()),))
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        selector = SelectClaimExport(
            service.selector.claims, service.selector.reports, service.selector.uow
        )
        access = await container.access_policy(session).context(user)
        with pytest.raises(InvalidRequest, match="kind is unavailable"):
            await resolve_side(selector, access, monitor)


async def test_resolver_rejects_revision_not_owned_by_watched_root(client, container, user):
    _, _, _, _, monitor = await seeded(client, container, user)
    watch = replace(monitor.watches[0], revision_id=uuid4())
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        access = await container.access_policy(session).context(user)
        with pytest.raises(NotFound):
            await resolve_side(service.selector, access, replace(monitor, watches=(watch,)))


async def test_resolver_rejects_valid_root_from_another_report(client, container, user):
    _, _, _, _, first = await seeded(client, container, user)
    _, _, _, _, second = await seeded(client, container, user)
    async with container.session_factory() as session:
        service = container.annotation_monitors(session)
        access = await container.access_policy(session).context(user)
        with pytest.raises(Conflict, match="exact report anchor"):
            await resolve_side(service.selector, access, replace(first, watches=second.watches))

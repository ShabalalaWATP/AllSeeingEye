"""Fresh execution, delivery and membership fences for operator removal."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.private_removal_graph import RemovalGraph
from ase.adapters.persistence.private_removal_selection import RemovalInventory
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.selected_index_models import SelectedIndexGateRow
from ase.adapters.persistence.teams import SqlTeamRepository, TeamMembershipRow
from ase.application.report_jobs.controls import require_discardable
from ase.application.research.phase_ledger import require_settled_source_ledger
from ase.domain.errors import AppError, Conflict
from ase.domain.private_removal import RemovalRequest, RemovalScope


async def execution_guards(
    session: AsyncSession,
    graph: RemovalGraph,
    inventory: RemovalInventory,
    request: RemovalRequest,
    now: datetime,
) -> None:
    if any(row.archived_at is None or row.enabled for row in graph.schedules):
        inventory.blockers.add("archive_subscriptions_first")
    if graph.schedule_ids:
        gate = await session.scalar(
            update(SelectedIndexGateRow)
            .where(SelectedIndexGateRow.id == 1)
            .values(revision=SelectedIndexGateRow.revision)
            .returning(SelectedIndexGateRow.id)
        )
        if gate is None:
            inventory.blockers.add("selected_index_gate_unavailable")
    for job_id in sorted(graph.job_ids):
        # Claims/checkpoints do not all use the administration guard.
        await session.execute(
            update(ReportJobRow)
            .where(ReportJobRow.id == job_id)
            .values(revision=ReportJobRow.revision)
            .execution_options(synchronize_session=False)
        )
        try:
            job = await SqlReportJobRepository(session).get(job_id)
            if job is None:
                raise Conflict("Job changed")
            require_discardable(job, now)
            require_settled_source_ledger(job.payload)
        except (AppError, ValueError, TypeError, KeyError):
            inventory.blockers.add("active_uncertain_or_unverifiable_job")
    if request.scope is RemovalScope.ACCOUNT:
        await manager_guard(session, request.owner_id, inventory)
    attempts = inventory.selections.get("subscription_edition_attempts")
    if attempts and await session.scalar(
        select(1)
        .select_from(attempts.table)
        .where(attempts.predicate, attempts.table.c.ended_at.is_(None))
        .limit(1)
    ):
        inventory.blockers.add("unsettled_subscription_attempt")
    await delivery_guards(session, inventory)
    assets = Base.metadata.tables["original_assets"]
    selected = inventory.selections.get("original_assets")
    if selected and await session.scalar(
        select(assets.c.id)
        .where(
            selected.predicate,
            assets.c.status.in_(("reserved", "uploading")),
            assets.c.reservation_expires_at > now,
        )
        .limit(1)
    ):
        inventory.blockers.add("active_original_asset_upload")


async def delivery_guards(session: AsyncSession, inventory: RemovalInventory) -> None:
    for name in ("subscription_delivery_outbox", "alert_notification_outbox", "web_push_outbox"):
        selected = inventory.selections.get(name)
        if selected is None:
            continue
        table = selected.table
        # A no-op UPDATE takes a portable row lock. Fresh state then decides;
        # an already released send is never assumed to have been recalled.
        ids: list[UUID] = list(
            await session.scalars(
                select(table.c.id).where(selected.predicate).order_by(table.c.id).limit(10_001)
            )
        )
        if len(ids) > 10_000:
            inventory.blockers.add("removal_inventory_limit_use_smaller_scopes")
            continue
        for start in range(0, len(ids), 100):
            await session.execute(
                update(table)
                .where(table.c.id.in_(ids[start : start + 100]))
                .values(state=table.c.state)
            )
        blocked = await session.scalar(
            select(table.c.id)
            .where(
                selected.predicate,
                table.c.state.not_in(
                    ("pending", "sent", "refused", "expired", "cancelled")
                    if name == "web_push_outbox"
                    else ("pending", "failed", "sent", "cancelled", "unavailable", "skipped")
                ),
            )
            .limit(1)
        )
        if blocked is not None:
            inventory.blockers.add("active_or_uncertain_delivery")


async def manager_guard(session: AsyncSession, owner: UUID, inventory: RemovalInventory) -> None:
    memberships = list(
        await session.scalars(
            select(TeamMembershipRow)
            .where(TeamMembershipRow.user_id == owner)
            .order_by(TeamMembershipRow.team_id)
            .limit(10_001)
        )
    )
    if len(memberships) > 10_000:
        inventory.blockers.add("removal_inventory_limit_use_smaller_scopes")
        return
    teams = SqlTeamRepository(session)
    for member in memberships:
        team = await teams.get_for_update(member.team_id)
        if team is None or not team.is_active or member.role != "manager":
            continue
        other = await session.scalar(
            select(TeamMembershipRow.user_id)
            .join(UserRow, UserRow.id == TeamMembershipRow.user_id)
            .where(
                TeamMembershipRow.team_id == member.team_id,
                TeamMembershipRow.user_id != owner,
                TeamMembershipRow.role == "manager",
                UserRow.is_active.is_(True),
            )
            .limit(1)
        )
        if other is None:
            inventory.blockers.add("last_active_team_manager")


async def logical_guards(
    session: AsyncSession, graph: RemovalGraph, inventory: RemovalInventory
) -> None:
    tables = Base.metadata.tables
    reports, jobs, briefs, schedules = (
        graph.report_ids,
        graph.job_ids,
        graph.brief_ids,
        graph.schedule_ids,
    )
    versions = select(tables["report_versions"].c.id).where(
        tables["report_versions"].c.report_id.in_(reports)
    )
    editions = select(tables["subscription_editions"].c.id).where(
        tables["subscription_editions"].c.subscription_id.in_(schedules)
    )
    # Incoming SQL FKs are checked separately against the exact captured rows.
    checks = (
        (
            "report_jobs",
            or_(
                tables["report_jobs"].c.report_id.in_(reports),
                tables["report_jobs"].c.version_id.in_(versions),
            ),
        ),
        ("schedules", tables["schedules"].c.last_report_id.in_(reports)),
        (
            "subscription_revisions",
            tables["subscription_revisions"].c.brief_revision_id.in_(briefs),
        ),
        (
            "subscription_editions",
            tables["subscription_editions"].c.covered_by_edition_id.in_(editions),
        ),
    )
    for name, predicate in checks:
        selected = inventory.selections[name]
        if await session.scalar(
            select(1).select_from(selected.table).where(predicate, ~selected.captured()).limit(1)
        ):
            inventory.blockers.add("retained_saved_work_dependency")
    passages = tables["original_passage_assets"]
    if await session.scalar(
        select(passages.c.id)
        .where(
            passages.c.job_id.in_(jobs),
            passages.c.report_version_id.is_not(None),
            passages.c.report_version_id.not_in(versions),
        )
        .limit(1)
    ):
        inventory.blockers.add("job_excerpts_used_by_retained_report")
    # Non-FK operational roots must not leave another owner's configuration dangling.
    for child, column, parent in (
        ("collection_plans", "aoi_id", "aois"),
        ("indicators", "plan_id", "collection_plans"),
        ("schedules", "plan_id", "collection_plans"),
    ):
        selected_parent = inventory.selections.get(parent)
        if selected_parent is None:
            continue
        table = tables[child]
        linked: ColumnElement[bool] = table.c[column].in_(
            select(selected_parent.table.c.id).where(selected_parent.captured())
        )
        child_selection = inventory.selections.get(child)
        if child_selection is not None:
            linked &= ~child_selection.captured()
        if await session.scalar(select(1).select_from(table).where(linked).limit(1)):
            inventory.blockers.add("retained_operational_dependency")

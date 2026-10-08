"""KAN-199: report deletion respects subscription history, versions are compare-and-set."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.citation_verdict_models import CitationVerdictRow
from ase.adapters.persistence.models import ReportRow, ReportVersionRow, ScheduleRow
from ase.adapters.persistence.reports import _version_row
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionEditionComparisonRow,
    SubscriptionEditionRow,
    SubscriptionLineageRow,
    SubscriptionRevisionRow,
)
from ase.application.dto import RequestContext
from ase.application.reports.access import SUBSCRIPTION_RETAINED
from ase.container import Container
from ase.domain.errors import Conflict
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_documents_helpers import document_records
from report_helpers import PROFILE
from report_input_helpers import CallbackGateway, NoPublicCollection, saved_parent


async def enforce_foreign_keys(session: AsyncSession) -> None:
    if session.get_bind().dialect.name == "sqlite":
        await session.execute(text("PRAGMA foreign_keys=ON"))
        assert await session.scalar(text("PRAGMA foreign_keys")) == 1


async def saved_report(container: Container, user: User) -> tuple[ReportRecord, ReportVersion]:
    record, version = document_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version


async def subscription(session: AsyncSession, container: Container, user: User) -> UUID:
    now = container.clock.now()
    schedule = ScheduleRow(
        id=uuid4(),
        team_id=None,
        name="Daily watch",
        template_id="intsum",
        hour_utc=6,
        cadence="daily",
        created_by=user.id,
        created_at=now,
        next_run_at=now + timedelta(days=1),
        enabled=True,
    )
    session.add(schedule)
    await session.flush()
    session.add(
        SubscriptionRevisionRow(
            subscription_id=schedule.id,
            revision=1,
            owner_id=user.id,
            team_id=None,
            request_snapshot="{}",
            compatibility_fingerprint="a" * 64,
            recurrence_policy="local_iana_v1",
            collection_policy="rolling_snapshot_v1",
            enabled=True,
            created_at=now,
        )
    )
    await session.flush()
    return schedule.id


def edition(subscription_id: UUID, container: Container, **links: object) -> SubscriptionEditionRow:
    due = container.clock.now() - timedelta(days=1)
    values: dict[str, object] = {
        "workflow": "completed",
        "report_quality": "ready",
        "coverage": "complete_for_plan",
        **links,
    }
    return SubscriptionEditionRow(
        id=uuid4(),
        subscription_id=subscription_id,
        trigger="scheduled",
        due_at_utc=due,
        request_uuid=None,
        frozen_revision=1,
        requested_start=due - timedelta(days=1),
        requested_end=due,
        effective_intervals=[],
        gaps=[],
        compatibility_fingerprint="a" * 64,
        created_at=due,
        updated_at=due,
        revision=2,
        accepted_as_baseline=False,
        **values,
    )


async def test_subscription_edition_report_is_refused_with_409_and_kept(
    client: AsyncClient, container: Container, user: User
) -> None:
    record, version = await saved_report(container, user)
    async with container.session_factory() as session:
        schedule_id = await subscription(session, container, user)
        session.add(edition(schedule_id, container, report_id=record.id, version_id=version.id))
        await session.commit()
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.delete(f"/api/reports/{record.id}", headers=bearer(token))
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "conflict"
    assert response.json()["error"]["message"] == SUBSCRIPTION_RETAINED
    assert (await client.get(f"/api/reports/{record.id}", headers=bearer(token))).status_code == 200


@pytest.mark.parametrize("link", ["baseline", "comparison", "lineage"])
async def test_every_subscription_version_link_refuses_deletion(
    container: Container, user: User, link: str
) -> None:
    pinned, pinned_version = await saved_report(container, user)
    produced, produced_version = await saved_report(container, user)
    async with container.session_factory() as session:
        await enforce_foreign_keys(session)
        schedule_id = await subscription(session, container, user)
        current = edition(
            schedule_id, container, report_id=produced.id, version_id=produced_version.id
        )
        if link == "baseline":
            current.baseline_version_id = pinned_version.id
        session.add(current)
        await session.flush()
        if link == "comparison":
            session.add(
                SubscriptionEditionComparisonRow(
                    edition_id=current.id,
                    previous_version_id=pinned_version.id,
                    current_version_id=produced_version.id,
                    state="assessment_changed",
                    result={},
                    created_at=container.clock.now(),
                )
            )
        if link == "lineage":
            session.add(
                SubscriptionLineageRow(
                    subscription_id=schedule_id,
                    compatibility_fingerprint="a" * 64,
                    analytical_baseline_version_id=pinned_version.id,
                    covered_intervals=[],
                    complete_cutoff=None,
                    updated_at=container.clock.now(),
                    revision=1,
                )
            )
        await session.commit()
        with pytest.raises(Conflict, match="subscription's saved edition history"):
            await container.delete_report(session).execute(user, pinned.id, context())
        await session.rollback()
        assert await session.get(ReportRow, pinned.id) is not None


@pytest.mark.parametrize("enforced", [True, False])
async def test_unpinned_report_deletes_its_citation_verdicts(
    container: Container, user: User, enforced: bool
) -> None:
    record, version = await saved_report(container, user)
    other, other_version = await saved_report(container, user)
    async with container.session_factory() as session:
        if enforced:
            await enforce_foreign_keys(session)
        for report, saved in ((record, version), (other, other_version)):
            session.add(verdict(report.id, saved.id, user.id, container))
        await session.commit()
        await container.delete_report(session).execute(user, record.id, context())
        assert await session.get(ReportRow, record.id) is None
        remaining = await session.scalars(select(CitationVerdictRow.report_id))
        assert list(remaining) == [other.id]


async def test_add_version_is_compare_and_set(container: Container, user: User) -> None:
    record, version = await saved_report(container, user)
    second = replace(version, id=uuid4(), number=2)
    rival = replace(version, id=uuid4(), number=2)
    async with container.session_factory() as session:
        reports = container.repositories(session).reports
        await reports.add_version(replace(record, latest_version=2), second)
        await session.commit()
        with pytest.raises(Conflict, match="Another request saved a new version"):
            await reports.add_version(replace(record, latest_version=2), rival)
        await session.rollback()
        numbers = await session.scalars(
            select(ReportVersionRow.id).where(
                ReportVersionRow.report_id == record.id, ReportVersionRow.number == 2
            )
        )
        assert list(numbers) == [second.id]
        assert (await reports.get(record.id)).latest_version == 2
        with pytest.raises(ValueError, match="latest version"):
            await reports.add_version(record, replace(version, id=uuid4(), number=3))


async def test_legacy_duplicate_numbers_read_the_first_saved_version(
    container: Container, user: User
) -> None:
    record, version = await saved_report(container, user)
    later = replace(version, id=uuid4(), created_at=version.created_at + timedelta(minutes=5))
    async with container.session_factory() as session:
        # A duplicate written before the guard existed, bypassing add_version.
        session.add(_version_row(later))
        await session.commit()
        reports = container.repositories(session).reports
        for _ in range(3):
            assert (await reports.get_version(record.id, 1)).id == version.id
        count = await session.scalar(
            select(func.count()).where(ReportVersionRow.report_id == record.id)
        )
        assert count == 2


async def test_regeneration_that_loses_a_race_is_refused_without_a_duplicate(
    container: Container, user: User
) -> None:
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})
    record, version = await saved_parent(container, user)
    rival = replace(version, id=uuid4(), number=2)

    async def concurrent_regeneration() -> None:
        async with container.session_factory() as other:
            reports = container.repositories(other).reports
            await reports.add_version(replace(record, latest_version=2), rival)
            await other.commit()

    container.llm = CallbackGateway(concurrent_regeneration)
    container.research = NoPublicCollection()
    async with container.session_factory() as session:
        with pytest.raises(Conflict, match="Another request saved a new version"):
            await container.generate_report(session).regenerate(user, record.id, context())
    async with container.session_factory() as session:
        numbers = await session.scalars(
            select(ReportVersionRow.number).where(ReportVersionRow.report_id == record.id)
        )
        assert sorted(numbers) == [1, 2]
        saved = await container.repositories(session).reports.get_version(record.id, 2)
        assert saved is not None and saved.id == rival.id


def verdict(
    report_id: UUID, version_id: UUID, owner: UUID, container: Container
) -> CitationVerdictRow:
    return CitationVerdictRow(
        id=uuid4(),
        report_id=report_id,
        report_version_id=version_id,
        version_number=1,
        judgement_id="KJ1",
        label="E1",
        relation="supporting",
        verdict="supports",
        note=None,
        owner_id=owner,
        team_id=None,
        reviewer_id=owner,
        recorded_at=container.clock.now(),
    )


def context() -> RequestContext:
    return RequestContext()

"""Seed scoped alerts and sign in the warning desk actors for bell tests."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID, uuid4

from httpx import AsyncClient

from ase.adapters.persistence.warning_mapping import _alert_row
from ase.container import Container
from ase.domain.warning import Alert
from helpers import USER_PASSWORD, bearer, login_token
from warning_scope_helpers import WarningActors

BELL = "/api/bell"


def make_alert(
    container: Container,
    created_by: UUID,
    team_id: UUID | None = None,
    *,
    hours_ago: float = 1,
    title: str = "Kharkiv strikes",
    indicator_id: UUID | None = None,
    report_id: UUID | None = None,
    monitor: tuple[UUID, UUID] | None = None,
    acknowledged: bool = False,
) -> Alert:
    fired = container.clock.now() - timedelta(hours=hours_ago)
    return Alert(
        id=uuid4(),
        indicator_id=None if monitor else (indicator_id or uuid4()),
        fired_at=fired,
        title=title,
        summary="Three reports near the rail yard.",
        count=3,
        threshold=2,
        event_ids=(),
        countries=("UA",),
        annotation_monitor_id=monitor[0] if monitor else None,
        annotation_transition_id=monitor[1] if monitor else None,
        acknowledged_at=fired if acknowledged else None,
        acknowledged_by=created_by if acknowledged else None,
        report_id=report_id,
        created_by=created_by,
        team_id=team_id,
    )


async def add_alerts(container: Container, *alerts: Alert) -> None:
    async with container.session_factory() as session:
        session.add_all([_alert_row(item) for item in alerts])
        await session.commit()


async def desk_headers(client: AsyncClient, actors: WarningActors) -> dict[str, dict[str, str]]:
    """Bearer headers for each warning desk actor, keyed by a short role name."""
    return {
        name: bearer(await login_token(client, actor.email, USER_PASSWORD))
        for name, actor in (
            ("owner", actors.owner),
            ("peer", actors.peer),
            ("manager", actors.manager),
            ("outsider", actors.outsider),
        )
    }

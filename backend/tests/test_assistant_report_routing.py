"""Ask Eye on a saved report routes through the report's binding, never the actor's."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from ase.application.assistant.report_context import ReportContextReader
from ase.application.assistant.service import routing_binding
from ase.domain.assistant import (
    AssistantAlertContext,
    AssistantContext,
    AssistantQuestion,
    AssistantReportContext,
    AssistantReportSelection,
)
from ase.domain.users import Role
from assistant_helpers import Gateway, nothing, profile
from helpers import create_user
from report_documents_helpers import document_records


def _context(*, report=None, alert=None) -> AssistantContext:
    return AssistantContext((), 0, 0, False, (), report=report, alert=alert)


def _report(team_id=None, created_by=None) -> AssistantReportContext:
    return AssistantReportContext(
        uuid4(), uuid4(), 1, "Report", datetime(2026, 9, 1, tzinfo=UTC), team_id, created_by
    )


def test_team_report_routes_through_its_team_binding():
    actor, owner, team = create_actor(), uuid4(), uuid4()
    assert routing_binding(actor, _context(report=_report(team, owner))) == (team, owner)


def test_personal_report_routes_through_its_owner_not_the_actor():
    actor, owner = create_actor(), uuid4()
    assert routing_binding(actor, _context(report=_report(None, owner))) == (None, owner)


def test_alert_and_unscoped_routing_are_unchanged():
    actor, owner, team = create_actor(), uuid4(), uuid4()
    alert = AssistantAlertContext(uuid4(), 1, 1, 1, owner, team)
    assert routing_binding(actor, _context(alert=alert)) == (team, owner)
    assert routing_binding(actor, _context()) == (None, actor.id)


def create_actor():
    class Actor:
        id = uuid4()

    return Actor()  # type: ignore[return-value]


class RecordingRouting:
    def __init__(self, inner):
        self.inner, self.calls = inner, []

    async def snapshot(self, **kwargs):
        self.calls.append(kwargs)
        return await self.inner.snapshot(**kwargs)


async def test_admin_asking_about_another_users_report_uses_the_owners_binding(container, user):
    record, first = document_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, first)
        await container.repositories(session).uow.commit()
    admin = await create_user(
        container, email="admin-eye@example.com", password=None, role=Role.ADMIN
    )
    await profile(container)
    gateway = Gateway()
    gateway.content = json.dumps(
        {"paragraphs": [{"kind": "finding", "text": "Fighting is reported.", "citations": ["E1"]}]}
    )
    container.llm = gateway
    async with container.session_factory() as session:
        service = container.map_assistant(session)
        service.report_reader = ReportContextReader(container.get_report(session))
        service.routing = RecordingRouting(service.routing)
        question = AssistantQuestion(
            "El Fasher fighting", scope="report", report=AssistantReportSelection(record.id, 1)
        )
        answer = await service.execute(admin, question, check_session=nothing)
    assert answer.context.report is not None and answer.context.report.created_by == user.id
    assert service.routing.calls == [{"team_id": None, "personal_owner_id": user.id}]

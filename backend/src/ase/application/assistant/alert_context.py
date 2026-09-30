"""Authorised, bounded current evidence referenced by an alert, never a frozen firing."""

from dataclasses import replace

from ase.application.access import AccessPolicy
from ase.application.assistant.sources import event_source, source_text_size
from ase.application.ports.feeds import EventStore
from ase.application.ports.source_controls import SourceAdmission
from ase.application.ports.warning import AlertRepository
from ase.domain.assistant import (
    AssistantAlertContext,
    AssistantContext,
    AssistantQuestion,
    AssistantSource,
)
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.users import User
from ase.domain.warning import MAX_EVIDENCE, Alert

MAX_CHARS = 24_000


class AlertContextReader:
    def __init__(
        self,
        alerts: AlertRepository,
        access: AccessPolicy,
        store: EventStore,
        admission: SourceAdmission,
    ) -> None:
        self.alerts, self.access = alerts, access
        self.store, self.admission = store, admission

    async def _read(
        self, actor: User, question: AssistantQuestion, *, for_update: bool = False
    ) -> Alert:
        if question.scope != "alert" or question.alert_id is None:
            raise InvalidRequest("Select an alert for its retained evidence.")
        access = await self.access.context(actor, for_update=for_update)
        alert = await self.alerts.get(question.alert_id)
        if alert is None:
            raise NotFound()
        access.require_read(alert.created_by, alert.team_id)
        return alert

    async def collect(self, actor: User, question: AssistantQuestion) -> AssistantContext:
        alert = await self._read(actor, question)
        identifiers = tuple(dict.fromkeys(alert.event_ids))[:MAX_EVIDENCE]
        events = [event for identifier in identifiers if (event := self.store.get(identifier))]
        enabled = await self.admission.enabled_many(tuple({event.source_id for event in events}))
        sources: list[AssistantSource] = []
        size = 0
        for event in events:
            source = event_source(event) if enabled.get(event.source_id, False) else None
            if source is None or size + source_text_size(source) > MAX_CHARS:
                continue
            size += source_text_size(source)
            sources.append(replace(source, id=f"E{len(sources) + 1}"))
        anchor = AssistantAlertContext(
            alert.id,
            alert.count,
            len(alert.event_ids),
            len(sources),
            alert.created_by,
            alert.team_id,
        )
        return AssistantContext(
            tuple(sources),
            len(identifiers),
            len({source.source_id for source in sources}),
            alert.count > len(sources),
            (
                "Currently retained evidence referenced by the alert, not an immutable "
                "snapshot of the original firing. Live corrections may have changed records.",
                f"Alert matched count: {alert.count}; stored sample size: {len(alert.event_ids)}; "
                f"available evidence included: {len(sources)}.",
                "Unavailable references may be absent, source-disabled, unsafe or outside "
                "the packet limit. Their unavailability does not establish expiry or absence.",
            ),
            matched_count=len(sources),
            alert=anchor,
            clarification=(
                "This alert has no usable retained event references. An evidence explanation "
                "is unavailable; no unrelated global sources were searched."
                if not sources
                else None
            ),
        )

    async def require_current(
        self, actor: User, anchor: AssistantAlertContext, *, for_update: bool = False
    ) -> None:
        current = await self._read(
            actor,
            AssistantQuestion("Check alert access", scope="alert", alert_id=anchor.id),
            for_update=for_update,
        )
        if (current.created_by, current.team_id) != (anchor.created_by, anchor.team_id):
            raise NotFound()

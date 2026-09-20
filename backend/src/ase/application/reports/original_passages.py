"""Release retained original excerpts under fresh report and source authority."""

from collections.abc import Awaitable, Callable, Mapping
from uuid import UUID

from ase.application.ports.original_passages import LinkedOriginalPassages
from ase.application.ports.services import Clock
from ase.application.ports.source_controls import SourceAdmission
from ase.application.reports.access import GetReportUseCase
from ase.application.research.original_policy import OriginalSourcePolicy
from ase.application.research.original_staging import StagedOriginalPassage
from ase.domain.errors import NotFound
from ase.domain.users import User


class ReadOriginalPassage:
    def __init__(
        self,
        passages: LinkedOriginalPassages,
        reports: GetReportUseCase,
        admission: SourceAdmission,
        policies: Mapping[str, OriginalSourcePolicy],
        clock: Clock,
    ) -> None:
        self._passages, self._reports = passages, reports
        self._admission, self._policies, self._clock = admission, policies, clock

    async def execute(
        self,
        actor: User,
        report_id: UUID,
        version_number: int,
        passage_ref: UUID,
        validate_session: Callable[[], Awaitable[None]],
    ) -> StagedOriginalPassage:
        report, version = await self._reports.execute(actor, report_id, version_number)
        receipt = version.research
        linked = (
            next(
                (
                    row
                    for row in receipt.original_followup
                    if row.passage_ref == passage_ref and row.status == "acquired"
                ),
                None,
            )
            if receipt is not None
            else None
        )
        if linked is None:
            raise NotFound()
        item = next((row for row in version.evidence if row.label == linked.evidence_label), None)
        if item is None or (item.event_id, item.source_id) != (linked.event_id, linked.source_id):
            raise NotFound()
        staged = await self._passages.linked(passage_ref, version.id, self._clock.now())
        if (
            staged is None
            or staged.job_id is None
            or staged.document.owner_id != report.created_by
            or staged.document.team_id != report.team_id
            or staged.evidence_label != linked.evidence_label
            or staged.event_id != linked.event_id
            or staged.document.id != linked.document_version_id
            or staged.document.passages[0].id != linked.passage_id
        ):
            raise NotFound()
        document = staged.document
        policy = self._policies.get(document.source_id)
        async with self._admission.guard():
            if (
                policy is None
                or policy.policy_id != document.acquisition_policy_id
                or not policy.permits(document.canonical_url, self._clock.now())
                or not await self._admission.enabled(document.source_id)
            ):
                raise NotFound()
            await self._reports.recheck(actor, report_id, version.number)
            # The source admission guard covers the final session recheck too.
            await validate_session()
        return staged

"""Resolve current authority, compare exact immutable inputs, then recheck before delivery."""

import asyncio
import re
from collections.abc import Callable
from dataclasses import replace
from typing import overload

from ase.application.dto import AccessClaims
from ase.application.ports import Clock
from ase.application.reports.claim_export_selection import SelectClaimExport, SelectedClaimExport
from ase.application.reports.comparison_inputs import ComparisonInput, ComparisonSelection
from ase.application.reports.comparison_manifest import comparison_digest, comparison_json
from ase.application.reports.comparison_release import recheck_comparison
from ase.application.reports.evidence_package import _PACKAGE_SLOTS
from ase.domain.annotation_comparison import COMPARISON_METHOD, AnnotationComparison, ComparisonSide
from ase.domain.annotation_deltas import annotation_deltas, evidence_deltas
from ase.domain.confidence_comparison import confidence_deltas
from ase.domain.errors import Conflict, InvalidRequest, RateLimited
from ase.domain.report_documents import ReportFile


def _side(selected: SelectedClaimExport) -> ComparisonSide:
    version = selected.version
    return ComparisonSide(
        selected.report_id,
        version.id,
        version.number,
        selected.record.title,
        version.period_from,
        version.period_to,
        version.created_at,
        version.data_cutoff,
        selected.evidence_sha256,
        selected.content_sha256,
        selected.revisions,
        selected.identity_revisions,
        selected.relationship_revisions,
        version.evidence,
        version.body.key_judgements,
        version.assessment,
    )


class AnnotationComparisons:
    def __init__(
        self,
        selector: SelectClaimExport,
        clock: Clock,
        renderer: Callable[[AnnotationComparison], bytes] = comparison_json,
    ) -> None:
        self.selector, self.clock, self.renderer = selector, clock, renderer

    async def _resolve(
        self, actor: AccessClaims, value: ComparisonSelection
    ) -> SelectedClaimExport:
        return await self.selector.resolve(
            actor,
            value.report_id,
            value.version_number,
            value.revisions,
            identity_references=value.identity_revisions,
            relationship_references=value.relationship_revisions,
            allow_empty=True,
        )

    @overload
    async def execute(
        self, actor: AccessClaims, value: ComparisonInput, expected_digest: None = None
    ) -> AnnotationComparison: ...

    @overload
    async def execute(
        self, actor: AccessClaims, value: ComparisonInput, expected_digest: str
    ) -> ReportFile: ...

    async def execute(
        self, actor: AccessClaims, value: ComparisonInput, expected_digest: str | None = None
    ) -> AnnotationComparison | ReportFile:
        if expected_digest is not None and re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None:
            raise InvalidRequest("Export requires the exact preview comparison digest.")
        if not _PACKAGE_SLOTS.acquire(blocking=False):
            raise RateLimited(5)
        task: asyncio.Task[tuple[AnnotationComparison, bytes]] | None = None
        try:
            old, new = (
                await self._resolve(actor, value.before),
                await self._resolve(actor, value.after),
            )
            if old.team_id != new.team_id or (old.team_id is None and old.owner_id != new.owner_id):
                raise InvalidRequest("Compared reports must share the same personal owner or team.")

            def render() -> tuple[AnnotationComparison, bytes]:
                before, after = _side(old), _side(new)
                try:
                    comparison = AnnotationComparison(
                        COMPARISON_METHOD,
                        self.clock.now(),
                        "",
                        actor.user_id,
                        before,
                        after,
                        value.correspondences,
                        value.judgement_correspondences,
                        annotation_deltas(before, after, value.correspondences),
                        evidence_deltas(before, after),
                        confidence_deltas(before, after, value.judgement_correspondences),
                    )
                except (ValueError, TypeError, StopIteration) as exc:
                    raise InvalidRequest(str(exc)) from exc
                comparison = replace(comparison, comparison_sha256=comparison_digest(comparison))
                if expected_digest is not None and comparison.comparison_sha256 != expected_digest:
                    raise Conflict(
                        "The selected comparison inputs, method or results changed. Preview again."
                    )
                return comparison, self.renderer(comparison)

            task = asyncio.create_task(asyncio.to_thread(render))
            task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
            comparison, content = await asyncio.shield(task)
            await recheck_comparison(self.selector, actor, (old, new))
            # Rendering cannot mutate side snapshots without invalidating the returned digest.
            if comparison_digest(comparison) != comparison.comparison_sha256:
                raise Conflict("Comparison content changed while rendering.")
            if expected_digest is None:
                return comparison
            return ReportFile(
                content, "application/json", f"comparison-{comparison.comparison_sha256[:16]}.json"
            )
        finally:
            if task is not None and not task.done():
                task.add_done_callback(lambda _: _PACKAGE_SLOTS.release())
            else:
                _PACKAGE_SLOTS.release()

"""Canonical immutable Research Brief definition, separate from a resolved run snapshot."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from typing import Any

from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_tasks import validate_registry_scope

from .research_brief_scope import BriefCollection, BriefObservation, BriefPrivateInput, BriefScope
from .research_brief_values import (
    BriefIdentity,
    BriefLens,
    BriefLimits,
    BriefMonitoring,
    BriefOutput,
    BriefQuestion,
    BriefValidationError,
)

# Do not exceed the existing report-job checkpoint byte cap at admission.
MAX_BRIEF_BYTES = 768 * 1024
_REQUIRED_CAP = {ResearchMode.QUICK: 3, ResearchMode.DETAILED: 6, ResearchMode.ADVANCED: 12}
_PRIVATE_FOCUS = {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}


@dataclass(frozen=True, slots=True)
class ResearchBrief:
    identity: BriefIdentity
    question: BriefQuestion
    scope: BriefScope
    observation: BriefObservation
    lens: BriefLens
    collection: BriefCollection
    output: BriefOutput
    limits: BriefLimits
    monitoring: BriefMonitoring
    private_inputs: tuple[BriefPrivateInput, ...] = ()

    def __post_init__(self) -> None:
        for field, kind in (
            ("identity", BriefIdentity),
            ("question", BriefQuestion),
            ("scope", BriefScope),
            ("observation", BriefObservation),
            ("lens", BriefLens),
            ("collection", BriefCollection),
            ("output", BriefOutput),
            ("limits", BriefLimits),
            ("monitoring", BriefMonitoring),
        ):
            if not isinstance(getattr(self, field), kind):
                raise BriefValidationError(field, "Use a validated brief section")
        if (
            not isinstance(self.private_inputs, tuple)
            or len(self.private_inputs) > 8
            or any(not isinstance(row, BriefPrivateInput) for row in self.private_inputs)
        ):
            raise BriefValidationError(
                "private_inputs", "Use at most eight durable input references"
            )
        keys = [
            (
                row.kind,
                row.input_id if row.kind == "session" else (row.report_id, row.report_version),
            )
            for row in self.private_inputs
        ]
        if len(set(keys)) != len(keys):
            raise BriefValidationError("private_inputs", "Input references must be unique")
        required = sum(row.required for row in self.question.requirements)
        if required > _REQUIRED_CAP[self.output.depth]:
            raise BriefValidationError(
                "question.requirements",
                "Reduce required questions or choose a deeper research tier",
            )
        if self.observation.time_basis is EvidenceTimeBasis.RECORDED and (
            self.observation.policy != "explicit" or self.scope.focus is not ResearchFocus.GENERAL
        ):
            raise BriefValidationError(
                "observation.time_basis",
                "Recorded history needs an explicit general-research interval",
            )
        if self.scope.focus in _PRIVATE_FOCUS:
            if not self.private_inputs and self.scope.parent_report_id is None:
                raise BriefValidationError(
                    "private_inputs", "Private research needs an authorised input"
                )
            if (
                self.collection.terms
                or self.collection.query_variants
                or self.collection.source_ids is not None
                or self.collection.web_search
                or self.collection.candidate_hypotheses
                or self.collection.planned_tasks
            ):
                raise BriefValidationError(
                    "collection", "Private input queries cannot enter public collection"
                )
        try:
            validate_registry_scope(
                self.collection.planned_tasks,
                self.scope.focus is ResearchFocus.COMPANY and self.scope.effective_area is None,
            )
        except ValueError as exc:
            raise BriefValidationError("collection.planned_tasks", str(exc)) from exc
        if self.scope.area is not None and (
            self.scope.country_isos
            or self.scope.focus is not ResearchFocus.GENERAL
            or self.scope.plan_id is not None
            or self.scope.conflict_id is not None
            or self.scope.hazard is not None
            or self.scope.categories
            or self.private_inputs
        ):
            raise BriefValidationError(
                "scope.area", "A drawn area needs a standalone general question"
            )
        if self._serialized_size() > MAX_BRIEF_BYTES:
            raise BriefValidationError("brief", "Research Brief exceeds its checkpoint size budget")

    def _serialized_size(self) -> int:
        try:
            return len(
                json.dumps(asdict(self), ensure_ascii=False, allow_nan=False, default=str).encode(
                    "utf-8"
                )
            )
        except (TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise BriefValidationError(
                "brief", "Research Brief cannot be safely serialised"
            ) from exc

    def revise(self, *, at: datetime, **changes: Any) -> ResearchBrief:
        """Create a new unpublished revision; the source revision remains untouched."""
        if "identity" in changes:
            raise BriefValidationError("identity", "Revision ownership and history are immutable")
        if not isinstance(at, datetime) or at.utcoffset() is None or at <= self.identity.revised_at:
            raise BriefValidationError("revised_at", "Revision time must advance")
        identity = replace(
            self.identity,
            revision=self.identity.revision + 1,
            revised_at=at.astimezone(UTC),
            published=False,
        )
        return replace(self, identity=identity, **changes)

    def require_subscription_ready(self, *, now: datetime) -> None:
        """Session imports cannot silently become permanent subscription attachments."""
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise BriefValidationError("observation", "Admission needs an aware clock")
        if any(row.requires_renewal for row in self.private_inputs):
            raise BriefValidationError(
                "private_inputs", "Renew session inputs or use authorised durable report evidence"
            )

    def require_live_inputs(self, *, now: datetime) -> None:
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise BriefValidationError("observation", "Admission needs an aware clock")
        if any(row.expires_at is not None and row.expires_at <= now for row in self.private_inputs):
            raise BriefValidationError("private_inputs", "A private input has expired; renew it")

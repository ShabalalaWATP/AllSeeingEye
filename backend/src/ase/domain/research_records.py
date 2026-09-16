"""Frozen collection coverage, excluding unselected raw items."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from ase.domain.area_context import AreaContext, context_from_dict, context_to_dict
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.original_followup import (
    MAX_ORIGINAL_RECEIPTS,
    OriginalFollowupReceipt,
    original_receipt_from_dict,
    original_receipt_to_dict,
)
from ase.domain.query_variant_records import (
    omit_variant_defaults,
    required_variant,
    variant_from_dict,
)
from ase.domain.registry_identifiers import lookup_from_dict
from ase.domain.research import (
    CollectionAttempt,
    CollectionPass,
    CollectionStatus,
    ResearchQuery,
)
from ase.domain.research_area import area_from_dict, area_to_dict
from ase.domain.research_capacity import MAX_COLLECTION_RECEIPTS, MAX_PLAN_TASKS
from ase.domain.research_continuation import continuation_from_dict
from ase.domain.research_plan import QueryTransformation, ResearchPlan, ResearchTask
from ase.domain.research_planning import planning_from_dict
from ase.domain.research_receipt_description import describe_receipt
from ase.domain.research_tasks import candidate_from_dict
from ase.domain.web_research import (
    WebResearchRecord,
    web_research_from_dict,
    web_research_to_dict,
)


@dataclass(frozen=True, slots=True)
class ResearchReceipt:
    question: str
    mode: str
    focus: str
    languages: tuple[str, ...]
    terms: tuple[str, ...]
    since: datetime
    until: datetime
    attempts: tuple[CollectionAttempt, ...]
    collected_items: int
    policy_version: str = "ase-research-v1"
    plan: ResearchPlan | None = None
    passes: tuple[CollectionPass, ...] = ()
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION
    web_research: WebResearchRecord | None = None
    original_followup: tuple[OriginalFollowupReceipt, ...] = ()
    # Added after historical exports were hashed; absent by default, see canonical_provenance.
    area_context: AreaContext | None = None

    @classmethod
    def build(
        cls,
        query: ResearchQuery,
        attempts: tuple[CollectionAttempt, ...],
        count: int,
        plan: ResearchPlan | None = None,
        passes: tuple[CollectionPass, ...] = (),
    ) -> "ResearchReceipt":
        return cls(
            query.question,
            query.mode.value,
            query.focus.value,
            query.languages,
            query.terms,
            query.since,
            query.until,
            attempts,
            count,
            plan=plan,
            passes=passes,
            time_basis=query.effective_time_basis,
        )

    @property
    def temporal_notice(self) -> str:
        if self.time_basis is EvidenceTimeBasis.RECORDED:
            return (
                "Project commitment years use uncertainty intervals; a partial-year overlap "
                "is only a possible temporal match. Other observations use acquisition, "
                "and reporting uses publication. Retrieval dates are never substituted."
            )
        if self.time_basis is EvidenceTimeBasis.RESEARCH:
            return (
                "Dates filter acquisition time for observations and publication time "
                "for reporting, "
                "not retrieval time. This does not establish complete event-time coverage."
            )
        return "Dates filter publication time, not necessarily event time."

    def describe(self) -> str:
        context = f" {self.area_context.describe()}" if self.area_context else ""
        return describe_receipt(self) + context


def research_to_dict(receipt: ResearchReceipt) -> dict[str, Any]:
    result = asdict(receipt)
    result["since"] = receipt.since.isoformat()
    result["until"] = receipt.until.isoformat()
    result["time_basis"] = receipt.time_basis.value
    if receipt.web_research is not None:
        result["web_research"] = web_research_to_dict(receipt.web_research)
    else:
        result.pop("web_research", None)
    result.pop("original_followup", None)
    result.pop("area_context", None)
    if receipt.area_context is not None:
        result["area_context"] = context_to_dict(receipt.area_context)
    result.update(
        {"original_followup": [original_receipt_to_dict(row) for row in receipt.original_followup]}
        if receipt.original_followup
        else {}
    )
    if receipt.plan is not None:
        result["plan"]["since"] = receipt.plan.since.isoformat()
        result["plan"]["until"] = receipt.plan.until.isoformat()
        result["plan"]["area"] = area_to_dict(receipt.plan.area)
    for row, original in zip(result["passes"], receipt.passes, strict=True):
        if row["plan"] is not None:
            row["plan"]["since"] = row["plan"]["since"].isoformat()
            row["plan"]["until"] = row["plan"]["until"].isoformat()
            row["plan"]["area"] = area_to_dict(original.plan.area) if original.plan else None
    # Optional additions stay absent when serialising legacy records.
    for attempt in result["attempts"]:
        _omit_legacy_task_defaults(attempt)
    for plan in [result.get("plan"), *(row.get("plan") for row in result["passes"])]:
        if plan is not None:
            _omit_legacy_plan_defaults(plan)
            for task in plan["tasks"]:
                _omit_legacy_task_defaults(task)
    for row in result["passes"]:
        for attempt in row["attempts"]:
            _omit_legacy_task_defaults(attempt)
    return result


def _omit_legacy_plan_defaults(plan: dict[str, Any]) -> None:
    _omit_translation_defaults(plan)
    _omit_scope_defaults(plan)
    for name in ("planning", "continuation"):
        if plan.get(name) is None:
            plan.pop(name, None)
    trace = plan.get("planning")
    if trace is not None:
        for row in trace.get("proposed_candidates", ()):
            if not row.get("registry_identifiers"):
                row.pop("registry_identifiers", None)
        for row in trace.get("proposed_tasks", ()):
            if row.get("route") == "terms":
                row.pop("route", None)
            if row.get("identifier_id") is None:
                row.pop("identifier_id", None)
    if not plan.get("candidate_hypotheses"):
        plan.pop("candidate_hypotheses", None)
    for candidate in plan.get("candidate_hypotheses", ()):
        if not candidate.get("registry_identifiers"):
            candidate.pop("registry_identifiers", None)
        if candidate.get("origin") == "operator":
            candidate.pop("origin", None)


def _omit_scope_defaults(plan: dict[str, Any]) -> None:
    countries = plan.get("country_isos")
    if countries and tuple(countries) == (plan.get("country_iso"),):
        plan.pop("country_isos", None)
    for key in ("research_web_search", "country_isos"):
        if not plan.get(key):
            plan.pop(key, None)


def _omit_legacy_task_defaults(row: dict[str, Any]) -> None:
    if row.get("query_variant") is not None:
        omit_variant_defaults(row["query_variant"])
    for key, default in (
        ("task_id", None),
        ("purpose", "baseline"),
        ("candidate_id", None),
        ("planned_terms_supported", False),
        ("registry_lookup", None),
        ("query_variant", None),
        ("registry_namespaces", ()),
        ("registry_options", ()),
    ):
        if row.get(key) == default:
            row.pop(key, None)


def research_from_dict(data: Mapping[str, Any] | None) -> ResearchReceipt | None:
    if data is None:
        return None
    if data.get("policy_version") != "ase-research-v1":
        raise ValueError("Unsupported research receipt policy")
    attempts = data.get("attempts", [])
    if not isinstance(attempts, list | tuple) or len(attempts) > MAX_COLLECTION_RECEIPTS:
        raise ValueError("Invalid collection receipts")
    originals = data.get("original_followup", ())
    if type(originals) not in (list, tuple) or len(originals) > MAX_ORIGINAL_RECEIPTS:
        raise ValueError("Invalid original follow-through receipts")
    return ResearchReceipt(
        question=str(data["question"]),
        mode=str(data["mode"]),
        focus=str(data["focus"]),
        languages=tuple(data["languages"]),
        terms=tuple(data["terms"]),
        since=datetime.fromisoformat(data["since"]),
        until=datetime.fromisoformat(data["until"]),
        attempts=tuple(
            CollectionAttempt(
                source_id=item["source_id"],
                source_name=item["source_name"],
                status=CollectionStatus(item["status"]),
                result_count=item["result_count"],
                explanation=item["explanation"],
                language=item.get("language"),
                task_id=item.get("task_id"),
                purpose=item.get("purpose", "baseline"),
                candidate_id=item.get("candidate_id"),
                registry_lookup=lookup_from_dict(item.get("registry_lookup")),
                query_variant=variant_from_dict(item.get("query_variant")),
            )
            for item in attempts
        ),
        collected_items=int(data["collected_items"]),
        plan=plan_from_dict(data.get("plan")),
        passes=passes_from_dict(data.get("passes", ())),
        time_basis=EvidenceTimeBasis(data.get("time_basis", "publication")),
        web_research=web_research_from_dict(data.get("web_research")),
        original_followup=tuple(original_receipt_from_dict(row) for row in originals),
        area_context=context_from_dict(data.get("area_context")),
    )


def plan_from_dict(data: Mapping[str, Any] | None) -> ResearchPlan | None:
    if data is None:
        return None
    if (
        data.get("policy_version") != "ase-deterministic-plan-v1"
        or len(data["tasks"]) > MAX_PLAN_TASKS
    ):
        raise ValueError("Invalid frozen research plan")
    values = dict(data)
    values["since"] = datetime.fromisoformat(data["since"])
    values["until"] = datetime.fromisoformat(data["until"])
    values["languages"] = tuple(data["languages"])
    values["area"] = area_from_dict(data.get("area"))
    values["time_basis"] = EvidenceTimeBasis(
        data.get("time_basis", "acquisition_or_publication" if values["area"] else "publication")
    )
    values["candidate_hypotheses"] = tuple(
        candidate_from_dict(row) for row in data.get("candidate_hypotheses", ())
    )
    values["planning"] = planning_from_dict(data.get("planning"))
    values["continuation"] = continuation_from_dict(data.get("continuation"))
    values["tasks"] = tuple(
        ResearchTask(
            **{
                **row,
                "terms": tuple(row["terms"]),
                "registry_lookup": lookup_from_dict(row.get("registry_lookup")),
                "query_variant": variant_from_dict(row.get("query_variant")),
                "registry_namespaces": tuple(row.get("registry_namespaces", ())),
                "registry_options": tuple(
                    lookup_from_dict(item) for item in row.get("registry_options", ())
                ),
            }
        )
        for row in data["tasks"]
    )
    translation = values.get("translation")
    if translation is not None:
        if translation.get("policy_version") != "ase-query-translation-v1":
            raise ValueError("Unsupported query transformation")
        values["translation"] = QueryTransformation(
            original_terms=tuple(translation["original_terms"]),
            languages=tuple(translation["languages"]),
            model=translation["model"],
            status=translation["status"],
            variants=tuple(required_variant(row) for row in translation["variants"]),
        )
    return ResearchPlan(**values)


def passes_from_dict(data: Any) -> tuple[CollectionPass, ...]:
    if not isinstance(data, list | tuple) or len(data) > 2:
        raise ValueError("Invalid collection passes")
    return tuple(
        CollectionPass(
            tuple(row["terms"]),
            tuple(
                CollectionAttempt(
                    **{
                        **attempt,
                        "status": CollectionStatus(attempt["status"]),
                        "registry_lookup": lookup_from_dict(attempt.get("registry_lookup")),
                        "query_variant": variant_from_dict(attempt.get("query_variant")),
                    }
                )
                for attempt in row["attempts"]
            ),
            plan_from_dict(row.get("plan")),
        )
        for row in data
    )


def _omit_translation_defaults(plan: dict[str, Any]) -> None:
    for row in (plan.get("translation") or {}).get("variants", ()):
        omit_variant_defaults(row)

"""Frozen collection coverage, excluding unselected raw items."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import (
    CollectionAttempt,
    CollectionPass,
    CollectionStatus,
    ResearchQuery,
)
from ase.domain.research_area import area_from_dict, area_to_dict
from ase.domain.research_plan import QueryTransformation, QueryVariant, ResearchPlan, ResearchTask


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
            time_basis=EvidenceTimeBasis.RESEARCH if query.area else EvidenceTimeBasis.PUBLICATION,
        )

    @property
    def temporal_notice(self) -> str:
        if self.time_basis is EvidenceTimeBasis.RESEARCH:
            return (
                "Dates filter acquisition time for observations and publication time "
                "for reporting, "
                "not retrieval time. This does not establish complete event-time coverage."
            )
        return "Dates filter publication time, not necessarily event time."

    def describe(self) -> str:
        statuses = "; ".join(
            f"{item.source_name}: {item.status.value}, {item.result_count} additional items. "
            f"{item.explanation}"
            for item in self.attempts
        )
        return (
            f"Collection coverage ({self.policy_version}): {statuses or 'No sources attempted.'} "
            f"{self.temporal_notice} Empty or unavailable "
            "sources do not establish absence of events. Collection does not verify claims."
        )


def research_to_dict(receipt: ResearchReceipt) -> dict[str, Any]:
    result = asdict(receipt)
    result["since"] = receipt.since.isoformat()
    result["until"] = receipt.until.isoformat()
    result["time_basis"] = receipt.time_basis.value
    if receipt.plan is not None:
        result["plan"]["since"] = receipt.plan.since.isoformat()
        result["plan"]["until"] = receipt.plan.until.isoformat()
        result["plan"]["area"] = area_to_dict(receipt.plan.area)
    for row, original in zip(result["passes"], receipt.passes, strict=True):
        if row["plan"] is not None:
            row["plan"]["since"] = row["plan"]["since"].isoformat()
            row["plan"]["until"] = row["plan"]["until"].isoformat()
            row["plan"]["area"] = area_to_dict(original.plan.area) if original.plan else None
    return result


def research_from_dict(data: Mapping[str, Any] | None) -> ResearchReceipt | None:
    if data is None:
        return None
    if data.get("policy_version") != "ase-research-v1":
        raise ValueError("Unsupported research receipt policy")
    attempts = data.get("attempts", [])
    if not isinstance(attempts, list | tuple) or len(attempts) > 64:
        raise ValueError("Invalid collection receipts")
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
            )
            for item in attempts
        ),
        collected_items=int(data["collected_items"]),
        plan=plan_from_dict(data.get("plan")),
        passes=passes_from_dict(data.get("passes", ())),
        time_basis=EvidenceTimeBasis(data.get("time_basis", "publication")),
    )


def plan_from_dict(data: Mapping[str, Any] | None) -> ResearchPlan | None:
    if data is None:
        return None
    if data.get("policy_version") != "ase-deterministic-plan-v1" or len(data["tasks"]) > 64:
        raise ValueError("Invalid frozen research plan")
    values = dict(data)
    values["since"] = datetime.fromisoformat(data["since"])
    values["until"] = datetime.fromisoformat(data["until"])
    values["languages"] = tuple(data["languages"])
    values["area"] = area_from_dict(data.get("area"))
    values["tasks"] = tuple(
        ResearchTask(**{**row, "terms": tuple(row["terms"])}) for row in data["tasks"]
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
            variants=tuple(
                QueryVariant(row["language"], tuple(row["terms"]))
                for row in translation["variants"]
            ),
        )
    return ResearchPlan(**values)


def passes_from_dict(data: Any) -> tuple[CollectionPass, ...]:
    if not isinstance(data, list | tuple) or len(data) > 2:
        raise ValueError("Invalid collection passes")
    return tuple(
        CollectionPass(
            tuple(row["terms"]),
            tuple(
                CollectionAttempt(**{**attempt, "status": CollectionStatus(attempt["status"])})
                for attempt in row["attempts"]
            ),
            plan_from_dict(row.get("plan")),
        )
        for row in data
    )

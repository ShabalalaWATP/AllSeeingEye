"""Frozen collection coverage, excluding unselected raw items."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchQuery,
)
from ase.domain.research_plan import ResearchPlan, ResearchTask


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

    @classmethod
    def build(
        cls,
        query: ResearchQuery,
        attempts: tuple[CollectionAttempt, ...],
        count: int,
        plan: ResearchPlan | None = None,
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
        )

    def describe(self) -> str:
        statuses = "; ".join(
            f"{item.source_name}: {item.status.value}, {item.result_count} additional items. "
            f"{item.explanation}"
            for item in self.attempts
        )
        return (
            f"Collection coverage ({self.policy_version}): {statuses or 'No sources attempted.'} "
            "Dates filter publication time, not necessarily event time. Empty or unavailable "
            "sources do not establish absence of events. Collection does not verify claims."
        )


def research_to_dict(receipt: ResearchReceipt) -> dict[str, Any]:
    result = asdict(receipt)
    result["since"] = receipt.since.isoformat()
    result["until"] = receipt.until.isoformat()
    if receipt.plan is not None:
        result["plan"]["since"] = receipt.plan.since.isoformat()
        result["plan"]["until"] = receipt.plan.until.isoformat()
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
    values["tasks"] = tuple(
        ResearchTask(**{**row, "terms": tuple(row["terms"])}) for row in data["tasks"]
    )
    return ResearchPlan(**values)

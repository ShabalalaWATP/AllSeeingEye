"""Explicit codecs for selected evidence, bounded collection context and cost totals."""

from dataclasses import asdict
from typing import Any, cast

from pydantic import TypeAdapter

from ase.application.report_jobs.codec_boundary import (
    canonical,
    count,
    encoded,
    identifier,
    json_copy,
    number,
    record,
    text,
    timestamp,
)
from ase.application.reports.production_types import Totals
from ase.domain.direction import Direction, direction_from_dict, direction_to_dict
from ase.domain.evidence import EvidenceItem
from ase.domain.llm import LlmUsage
from ase.domain.report_records import (
    evidence_from_list,
    evidence_to_list,
    findings_from_list,
    findings_to_list,
)
from ase.domain.research import ResearchQuery
from ase.domain.research_area import area_from_dict, area_to_dict
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict


def evidence_from_json(value: Any) -> tuple[EvidenceItem, ...]:
    if type(value) is not list or len(value) > 100:
        raise ValueError("Invalid frozen evidence count")
    result = evidence_from_list(value)
    for item in result:
        record(item)
        count(item.credibility, 6)
        if item.credibility < 1 or item.reliability not in "ABCDEF" or len(item.reliability) != 1:
            raise ValueError("Invalid frozen evidence grade")
        if item.grade != f"{item.reliability}{item.credibility}":
            raise ValueError("Invalid frozen evidence grade")
        if item.lon is not None:
            number(item.lon, -180, 180)
        if item.lat is not None:
            number(item.lat, -90, 90)
    if len({item.label for item in result}) != len(result) or len(
        {item.event_id for item in result}
    ) != len(result):
        raise ValueError("Duplicate frozen evidence identity")
    canonical(value, evidence_to_list(result))
    return result


def direction_from_json(value: Any) -> Direction | None:
    if value is None:
        return None
    result = record(direction_from_dict(value))
    canonical(value, direction_to_dict(result))
    return result


def query_to_dict(value: ResearchQuery | None) -> dict[str, Any] | None:
    if value is None:
        return None
    # ResearchQuery contains bounded search scope only, no raw inputs or credentials.
    return cast(
        dict[str, Any],
        json_copy(
            {
                "question": value.question,
                "since": value.since.isoformat(),
                "until": value.until.isoformat(),
                "languages": value.languages,
                "terms": value.terms,
                "mode": value.mode.value,
                "focus": value.focus.value,
                "country_iso": value.country_iso,
                "subject": value.subject,
                "source_ids": value.source_ids,
                "query_variants": [asdict(row) for row in value.query_variants],
                "area": area_to_dict(value.area),
                "time_basis": value.time_basis.value if value.time_basis else None,
                "candidate_hypotheses": [asdict(row) for row in value.candidate_hypotheses],
                "planned_tasks": [asdict(row) for row in value.planned_tasks],
                "country_isos": value.country_isos,
                "research_web_search": value.research_web_search,
            }
        ),
    )


def query_from_dict(value: Any) -> ResearchQuery | None:
    if value is None:
        return None
    if type(value) is not dict:
        raise ValueError("Invalid frozen collection query")
    area = area_from_dict(value.get("area"))
    typed_value = {**value, "area": asdict(area) if area else None}
    result = record(TypeAdapter(ResearchQuery).validate_json(encoded(typed_value), strict=True))
    canonical(value, query_to_dict(result))
    return result


def receipt_from_json(value: Any) -> ResearchReceipt | None:
    if value is None:
        return None
    result = research_from_dict(value)
    if result is None:
        raise ValueError("Missing collection receipt")
    record(result)
    count(result.collected_items, 100_000)
    if result.plan:
        for name in ("request_limit", "item_limit", "model_calls", "translation_calls", "replans"):
            count(getattr(result.plan, name), 100_000)
        number(result.plan.seconds_limit, 0, 86_400)
    canonical(value, research_to_dict(result))
    return result


def totals_to_dict(value: Totals) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json_copy(
            {
                "prompt_tokens": value.prompt_tokens,
                "completion_tokens": value.completion_tokens,
                "latency_ms": number(value.latency_ms, 0, 86_400_000),
                "findings": findings_to_list(tuple(value.findings)),
                "usage": [
                    {
                        "at": row.at.isoformat(),
                        "profile_id": str(row.profile_id),
                        "user_id": str(row.user_id) if row.user_id else None,
                        "purpose": row.purpose,
                        "ok": row.ok,
                        "latency_ms": number(row.latency_ms, 0, 86_400_000),
                        "prompt_tokens": row.prompt_tokens,
                        "completion_tokens": row.completion_tokens,
                    }
                    for row in value.usage
                ],
            }
        ),
    )


def _usage(value: Any) -> LlmUsage:
    keys = {
        "at",
        "profile_id",
        "user_id",
        "purpose",
        "ok",
        "latency_ms",
        "prompt_tokens",
        "completion_tokens",
    }
    if type(value) is not dict or set(value) != keys or type(value["ok"]) is not bool:
        raise ValueError("Invalid saved usage fields")
    purpose = text(value["purpose"], 120)
    if not purpose or any(not (char.isalnum() or char in "_-.:/") for char in purpose):
        raise ValueError("Invalid saved usage purpose")
    profile_id = identifier(value["profile_id"])
    if profile_id is None:
        raise ValueError("Saved usage requires a profile identifier")
    return LlmUsage(
        at=timestamp(value["at"]),
        profile_id=profile_id,
        user_id=identifier(value["user_id"]),
        purpose=purpose,
        ok=value["ok"],
        latency_ms=number(value["latency_ms"], 0, 86_400_000),
        prompt_tokens=_tokens(value["prompt_tokens"]),
        completion_tokens=_tokens(value["completion_tokens"]),
    )


def _tokens(value: Any) -> int | None:
    return None if value is None else count(value)


def totals_from_dict(value: Any) -> Totals:
    keys = {"prompt_tokens", "completion_tokens", "latency_ms", "findings", "usage"}
    if type(value) is not dict or set(value) != keys:
        raise ValueError("Invalid saved production totals")
    for key in ("findings", "usage"):
        if type(value[key]) is not list or len(value[key]) > 256:
            raise ValueError("Invalid saved production totals count")
    findings = findings_from_list(value["findings"])
    for finding in findings:
        record(finding)
        text(finding.rule, 120)
        text(finding.location, 300)
        text(finding.message, 4000)
    result = Totals(
        prompt_tokens=_tokens(value["prompt_tokens"]),
        completion_tokens=_tokens(value["completion_tokens"]),
        latency_ms=number(value["latency_ms"], 0, 86_400_000),
        findings=list(findings),
        usage=[_usage(row) for row in value["usage"]],
    )
    canonical(value, totals_to_dict(result))
    return result

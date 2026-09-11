"""Only explicit request settings and safe provenance can cross job admission."""

from dataclasses import replace
from hashlib import sha256
from typing import Any

from ase.application.report_jobs.codec_boundary import (
    canonical,
    count,
    encoded,
    identifier,
    json_copy,
    record,
    text,
    timestamp,
)
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import Template

_METADATA = {
    "research_input",
    "research_reuse",
    "parent_report_id",
    "parent_version",
    "collection_plan_revision",
}


def template_digest(template: Template) -> str:
    value = {
        "id": template.id,
        "title": template.title,
        "purpose": template.purpose,
        "sections": template.sections,
        "token_budget": template.token_budget,
        "role": template.role.value,
        "needs_question": template.needs_question,
        "needs_country": template.needs_country,
        "needs_conflict": template.needs_conflict,
        "needs_hazard": template.needs_hazard,
        "strategy": {
            "categories": sorted(row.value for row in template.strategy.categories),
            "window_hours": template.strategy.window_hours,
            "max_items": template.strategy.max_items,
            "per_source_cap": template.strategy.per_source_cap,
        },
    }
    return sha256(encoded(value).encode()).hexdigest()


def request_to_dict(request: ReportRequest) -> dict[str, Any]:
    return {
        "team_id": str(request.team_id) if request.team_id else None,
        "profile_id": str(request.profile_id) if request.profile_id else None,
        "automation": request.automation,
        "map_view_id": str(request.map_view_id) if request.map_view_id else None,
        "map_revision_id": str(request.map_revision_id) if request.map_revision_id else None,
    }


def _object(value: Any, keys: set[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise ValueError("Invalid frozen request metadata")
    return value


def _metadata(scope: dict[str, Any]) -> None:
    if ("parent_report_id" in scope) != ("parent_version" in scope):
        raise ValueError("Parent report must pin an exact saved version")
    if "parent_report_id" in scope and (
        identifier(scope["parent_report_id"]) is None or count(scope["parent_version"]) < 1
    ):
        raise ValueError("Invalid frozen parent version")
    if "research_input" in scope:
        value = _object(
            scope["research_input"],
            {"filename", "media_type", "sha256", "imported_at", "extracted_items", "limitations"},
        )
        text(value["filename"], 240)
        text(value["media_type"], 120)
        digest = text(value["sha256"], 64)
        if (
            digest is None
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise ValueError("Invalid frozen input digest")
        timestamp(value["imported_at"])
        count(value["extracted_items"], 1000)
        if type(value["limitations"]) is not list or len(value["limitations"]) > 100:
            raise ValueError("Invalid frozen input limitations")
        for line in value["limitations"]:
            text(line, 2000)
    if "research_reuse" in scope:
        value = _object(
            scope["research_reuse"], {"report_id", "version", "evidence_items", "basis"}
        )
        if (
            identifier(value["report_id"]) is None
            or count(value["version"]) < 1
            or value["basis"] != "frozen_saved_evidence"
        ):
            raise ValueError("Invalid frozen evidence provenance")
        count(value["evidence_items"], 100)
    if "collection_plan_revision" in scope:
        value = _object(scope["collection_plan_revision"], {"id", "updated_at"})
        if identifier(value["id"]) is None or value["id"] != scope.get("plan"):
            raise ValueError("Invalid frozen collection plan revision")
        timestamp(value["updated_at"])


def request_from_dict(value: Any, scope: Any, template: Template) -> ReportRequest:
    _object(value, {"team_id", "profile_id", "automation", "map_view_id", "map_revision_id"})
    if type(scope) is not dict or type(value["automation"]) is not bool:
        raise ValueError("Invalid frozen request")
    _metadata(scope)
    request = ReportRequest.from_scope(template.id, scope)
    request = replace(
        request,
        team_id=identifier(value["team_id"]),
        profile_id=identifier(value["profile_id"]),
        automation=value["automation"],
        map_view_id=identifier(value["map_view_id"]),
        map_revision_id=identifier(value["map_revision_id"]),
    )
    # Type validation is performed after the historical codec; the canonical comparison
    # below then catches its coercions and every unrecognised nested field.
    record(request)
    canonical(
        {key: item for key, item in scope.items() if key not in _METADATA},
        json_copy(report_scope(request, template)),
    )
    if request.map_view_id is not None and (
        request.map_origin is None
        or request.map_origin.view_id != request.map_view_id
        or request.map_origin.revision_id != request.map_revision_id
    ):
        raise ValueError("A saved map request must retain its exact map revision")
    if request.plan_id is not None and "collection_plan_revision" not in scope:
        raise ValueError("A collection plan request must retain its exact revision")
    if request.parent_report_id is not None and request.parent_version is None:
        raise ValueError("A follow-up request must retain its exact parent version")
    return request

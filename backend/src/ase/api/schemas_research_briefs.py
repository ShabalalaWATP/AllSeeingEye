"""Research Brief transport: server-owned identity and strict canonical definition."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from ase.application.ports.brief_management import BriefSummary
from ase.application.research.brief_codec import brief_from_dict, brief_to_dict
from ase.domain.map_research_origin import MapResearchOrigin, origin_from_dict
from ase.domain.research_area import (
    ResearchArea,
    area_from_dict,
    direct_area_from_geometry,
)
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_values import BriefIdentity, BriefValidationError

_IDENTITY = TypeAdapter(BriefIdentity)
_AREA = TypeAdapter(ResearchArea)
_ORIGIN = TypeAdapter(MapResearchOrigin)


def _canonical_datetime(value: object, field: str) -> object:
    if value is None or not isinstance(value, str):
        return value
    if not 20 <= len(value) <= 48 or "T" not in value:
        raise BriefValidationError(field, "Use a timezone-aware ISO date and time")
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.utcoffset() is None:
            raise ValueError("Timezone is missing")
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    except ValueError as exc:
        raise BriefValidationError(field, "Use a timezone-aware ISO date and time") from exc


def _normalise_scope(scope: dict[str, Any]) -> dict[str, Any]:
    """Accept the existing GeoJSON transport; server computes canonical geometry."""
    result = dict(scope)
    area = result.get("area")
    if (
        isinstance(area, dict)
        and isinstance(area.get("geometry"), dict)
        and "type" in area["geometry"]
    ):
        parsed: ResearchArea | None
        if set(area) == {"geometry"}:
            parsed = direct_area_from_geometry(area["geometry"])
        else:
            parsed = area_from_dict(area)
        if parsed is None:
            raise BriefValidationError("scope.area", "Choose a valid research area")
        result["area"] = _AREA.dump_python(parsed, mode="json")
    origin = result.get("map_origin")
    if isinstance(origin, dict) and isinstance(origin.get("area"), dict):
        origin_area = origin["area"]
        if isinstance(origin_area.get("geometry"), dict) and "type" in origin_area["geometry"]:
            parsed_origin = origin_from_dict(origin)
            if parsed_origin is None:
                raise BriefValidationError("scope.map_origin", "Choose an exact saved-map origin")
            result["map_origin"] = _ORIGIN.dump_python(parsed_origin, mode="json")
    return result


class ResearchBriefDraftIn(BaseModel):
    """The reusable definition is checked by the one strict domain codec."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120, strict=True)
    team_id: UUID | None = None
    preset_id: str | None = Field(default=None, max_length=64, strict=True)
    preset_version: int | None = Field(default=None, ge=1, strict=True)
    question: dict[str, Any]
    scope: dict[str, Any]
    observation: dict[str, Any]
    lens: dict[str, Any]
    collection: dict[str, Any]
    output: dict[str, Any]
    limits: dict[str, Any]
    monitoring: dict[str, Any]
    private_inputs: list[dict[str, Any]] = Field(default_factory=list, max_length=8)

    def to_brief(self, identity: BriefIdentity) -> ResearchBrief:
        try:
            fields = self.model_dump(mode="json")
            fields["scope"] = _normalise_scope(fields["scope"])
            for field in ("since", "until"):
                if field in fields["observation"]:
                    fields["observation"][field] = _canonical_datetime(
                        fields["observation"][field], f"observation.{field}"
                    )
            for index, private_input in enumerate(fields["private_inputs"]):
                if "expires_at" in private_input:
                    private_input["expires_at"] = _canonical_datetime(
                        private_input["expires_at"], f"private_inputs.{index}.expires_at"
                    )
        except BriefValidationError:
            raise
        except (TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise BriefValidationError(
                "scope", "Research Brief scope cannot be safely encoded"
            ) from exc
        return brief_from_dict(
            {
                "identity": _IDENTITY.dump_python(identity, mode="json"),
                **{
                    name: fields[name]
                    for name in (
                        "question",
                        "scope",
                        "observation",
                        "lens",
                        "collection",
                        "output",
                        "limits",
                        "monitoring",
                        "private_inputs",
                    )
                },
            }
        )


class ResearchBriefRevisionIn(ResearchBriefDraftIn):
    base_revision: int = Field(ge=1, strict=True)


class ResearchBriefOut(BaseModel):
    brief: dict[str, Any]

    @classmethod
    def from_brief(cls, brief: ResearchBrief) -> ResearchBriefOut:
        return cls(brief=brief_to_dict(brief))


class ResearchBriefSummaryOut(BaseModel):
    id: UUID
    revision: int
    owner_id: UUID
    team_id: UUID | None
    title: str
    schema_version: int
    origin: str
    published: bool
    created_at: datetime
    revised_at: datetime

    @classmethod
    def from_summary(cls, row: BriefSummary) -> ResearchBriefSummaryOut:
        return cls(
            id=row.id,
            revision=row.revision,
            owner_id=row.owner_id,
            team_id=row.team_id,
            title=row.title,
            schema_version=row.schema_version,
            origin=row.origin,
            published=row.published,
            created_at=row.created_at,
            revised_at=row.revised_at,
        )


class ResearchBriefPageOut(BaseModel):
    items: list[ResearchBriefSummaryOut]
    limit: int
    offset: int

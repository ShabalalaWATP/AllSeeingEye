"""Immutable identity, question and presentation choices for a Research Brief."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from ase.domain.languages import ReportLanguage, language_capability
from ase.domain.research import ResearchMode

BRIEF_SCHEMA_VERSION = 1
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}\Z")


class BriefValidationError(ValueError):
    """A safe field-addressed admission error, with no private value echoed."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(message)


def stable_id(value: object, field: str) -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise BriefValidationError(field, "Use a stable identifier of at most 64 characters")
    return value


def bounded_text(value: object, field: str, maximum: int, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or any((ord(char) < 32 and char not in "\t\n\r") or ord(char) == 127 for char in value)
    ):
        raise BriefValidationError(field, f"Enter bounded text of at most {maximum} characters")
    return value


def positive_version(value: object, field: str) -> int:
    if type(value) is not int or value < 1:
        raise BriefValidationError(field, "Choose a positive version number")
    return value


@dataclass(frozen=True, slots=True)
class BriefIdentity:
    id: UUID
    revision: int
    owner_id: UUID
    title: str
    created_at: datetime
    revised_at: datetime
    team_id: UUID | None = None
    preset_id: str | None = None
    preset_version: int | None = None
    schema_version: int = BRIEF_SCHEMA_VERSION
    origin: Literal["authored", "legacy-derived"] = "authored"
    published: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.owner_id, UUID):
            raise BriefValidationError("identity", "Brief and owner identifiers are required")
        if self.team_id is not None and not isinstance(self.team_id, UUID):
            raise BriefValidationError("team_id", "Choose an authorised team")
        positive_version(self.revision, "revision")
        if type(self.schema_version) is not int or self.schema_version != BRIEF_SCHEMA_VERSION:
            raise BriefValidationError(
                "schema_version", "Unsupported Research Brief schema version"
            )
        bounded_text(self.title, "title", 120)
        if (self.preset_id is None) != (self.preset_version is None):
            raise BriefValidationError("preset", "Pin both preset ID and version")
        if self.preset_id is not None:
            stable_id(self.preset_id, "preset_id")
            positive_version(self.preset_version, "preset_version")
        if self.origin not in ("authored", "legacy-derived"):
            raise BriefValidationError("origin", "Unknown brief origin")
        if type(self.published) is not bool:
            raise BriefValidationError("published", "Invalid publication state")
        if (
            not isinstance(self.created_at, datetime)
            or not isinstance(self.revised_at, datetime)
            or self.created_at.utcoffset() is None
            or self.revised_at.utcoffset() is None
            or self.revised_at < self.created_at
        ):
            raise BriefValidationError("revised_at", "Use ordered timezone-aware revision dates")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))
        object.__setattr__(self, "revised_at", self.revised_at.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class IntelligenceRequirement:
    id: str
    question: str
    required: bool = True
    priority: int = 1

    def __post_init__(self) -> None:
        stable_id(self.id, "requirements.id")
        bounded_text(self.question, "requirements.question", 500)
        if (
            type(self.required) is not bool
            or type(self.priority) is not int
            or not 1 <= self.priority <= 12
        ):
            raise BriefValidationError("requirements", "Choose required status and priority 1-12")


@dataclass(frozen=True, slots=True)
class BriefQuestion:
    main: str
    requirements: tuple[IntelligenceRequirement, ...] = ()
    exclusions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        bounded_text(self.main, "question.main", 2000)
        if (
            not isinstance(self.requirements, tuple)
            or len(self.requirements) > 12
            or any(not isinstance(row, IntelligenceRequirement) for row in self.requirements)
        ):
            raise BriefValidationError("question.requirements", "Use at most twelve requirements")
        if len({row.id for row in self.requirements}) != len(self.requirements):
            raise BriefValidationError("question.requirements", "Requirement IDs must be unique")
        if not isinstance(self.exclusions, tuple) or len(self.exclusions) > 10:
            raise BriefValidationError("question.exclusions", "Use at most ten exclusions")
        for exclusion in self.exclusions:
            bounded_text(exclusion, "question.exclusions", 300)


class LensId(StrEnum):
    GENERAL = "general"
    UK_POLICY = "uk_policy"
    CIVILIAN_PROTECTION = "civilian_protection"
    REGIONAL_SECURITY = "regional_security"
    ECONOMIC_EXPOSURE = "economic_exposure"
    ENERGY_SECURITY = "energy_security"
    SUPPLY_CHAIN = "supply_chain"
    DEFENSIVE_CYBER = "defensive_cyber"
    ACTOR_PERSPECTIVE = "actor_perspective"


@dataclass(frozen=True, slots=True)
class BriefLens:
    id: LensId = LensId.GENERAL
    audience: str | None = None
    decision_need: str | None = None
    relevance_instructions: str | None = None
    challenge_conclusions: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.id, LensId):
            raise BriefValidationError("lens.id", "Choose a supported analytic lens")
        for field in ("audience", "decision_need", "relevance_instructions"):
            bounded_text(getattr(self, field), f"lens.{field}", 1000, optional=True)
        if type(self.challenge_conclusions) is not bool:
            raise BriefValidationError("lens.challenge_conclusions", "Invalid challenge choice")


@dataclass(frozen=True, slots=True)
class BriefOutput:
    depth: ResearchMode
    language: ReportLanguage = "en"
    style: Literal["briefing", "assessment"] = "assessment"
    template_id: str = "ask"
    preferred_sections: tuple[str, ...] = ()
    chart_preference: Literal["auto", "prefer", "avoid"] = "auto"
    table_preference: Literal["auto", "prefer", "avoid"] = "auto"
    model_profile_id: UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.depth, ResearchMode):
            raise BriefValidationError("output.depth", "Choose Basic, Deep or Advanced")
        capability = language_capability(self.language) if isinstance(self.language, str) else None
        if capability is None or not capability.report_supported:
            raise BriefValidationError("output.language", "Choose a supported report language")
        if self.style not in ("briefing", "assessment"):
            raise BriefValidationError("output.style", "Choose a supported report style")
        stable_id(self.template_id, "output.template_id")
        if not isinstance(self.preferred_sections, tuple) or len(self.preferred_sections) > 16:
            raise BriefValidationError(
                "output.preferred_sections", "Choose at most sixteen sections"
            )
        for section in self.preferred_sections:
            stable_id(section, "output.preferred_sections")
        if len(set(self.preferred_sections)) != len(self.preferred_sections):
            raise BriefValidationError("output.preferred_sections", "Sections must be unique")
        if self.chart_preference not in (
            "auto",
            "prefer",
            "avoid",
        ) or self.table_preference not in ("auto", "prefer", "avoid"):
            raise BriefValidationError(
                "output.visuals", "Choose accessible chart and table preferences"
            )
        if self.model_profile_id is not None and not isinstance(self.model_profile_id, UUID):
            raise BriefValidationError("output.model_profile_id", "Invalid model profile reference")


@dataclass(frozen=True, slots=True)
class BriefLimits:
    """Optional user ceilings; admission must also check the selected model profile."""

    policy_id: str = "ase-brief-limits-v1"
    max_passes: int | None = None
    max_external_operations: int | None = None
    max_model_calls: int | None = None
    max_output_tokens: int | None = None
    max_collection_seconds: int | None = None

    def __post_init__(self) -> None:
        stable_id(self.policy_id, "limits.policy_id")
        for field, maximum in (
            ("max_passes", 2),
            ("max_external_operations", 32),
            ("max_model_calls", 24),
            ("max_output_tokens", 256_000),
            ("max_collection_seconds", 240),
        ):
            value = getattr(self, field)
            if value is not None and (type(value) is not int or not 1 <= value <= maximum):
                raise BriefValidationError(
                    f"limits.{field}", "Limit exceeds the current system cap"
                )


@dataclass(frozen=True, slots=True)
class BriefIndicator:
    id: str
    condition: str

    def __post_init__(self) -> None:
        stable_id(self.id, "monitoring.indicators.id")
        bounded_text(self.condition, "monitoring.indicators.condition", 500)


@dataclass(frozen=True, slots=True)
class BriefMonitoring:
    indicators: tuple[BriefIndicator, ...] = ()
    review_conditions: tuple[str, ...] = ()
    prefer_novelty: bool | None = None
    organisation_profile_id: UUID | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.indicators, tuple)
            or len(self.indicators) > 12
            or any(not isinstance(row, BriefIndicator) for row in self.indicators)
            or len({row.id for row in self.indicators}) != len(self.indicators)
        ):
            raise BriefValidationError(
                "monitoring.indicators", "Use at most twelve unique indicators"
            )
        if not isinstance(self.review_conditions, tuple) or len(self.review_conditions) > 8:
            raise BriefValidationError(
                "monitoring.review_conditions", "Use at most eight review conditions"
            )
        for condition in self.review_conditions:
            bounded_text(condition, "monitoring.review_conditions", 300)
        if self.prefer_novelty is not None and type(self.prefer_novelty) is not bool:
            raise BriefValidationError("monitoring.prefer_novelty", "Invalid novelty preference")
        if self.organisation_profile_id is not None and not isinstance(
            self.organisation_profile_id, UUID
        ):
            raise BriefValidationError(
                "monitoring.organisation_profile_id", "Invalid profile reference"
            )

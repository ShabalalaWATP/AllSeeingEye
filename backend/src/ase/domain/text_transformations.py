"""Immutable declared text transformations; original citation text is never replaced."""

import re
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from ase.domain.languages import valid_language_code


def validate_script(value: str | None) -> None:
    if value is not None and not re.fullmatch(r"[A-Z][a-z]{3}", value):
        raise ValueError("Use a four-letter ISO 15924 script code")


@dataclass(frozen=True, slots=True)
class TextTransformation:
    field: Literal["title", "summary"]
    original_text: str
    transformed_text: str
    kind: Literal["translation", "transliteration"]
    source_language: str
    target_language: str
    origin: Literal["operator", "source", "machine"]
    method: str
    source_script: str | None = None
    target_script: str | None = None
    actor_id: UUID | None = None
    review_status: Literal["unreviewed", "operator_declared"] = "unreviewed"
    limitations: tuple[str, ...] = ()
    model: str | None = None
    profile_id: UUID | None = None
    provider: str | None = None

    def __post_init__(self) -> None:
        if self.field not in {"title", "summary"} or self.kind not in {
            "translation",
            "transliteration",
        }:
            raise ValueError("Unknown text transformation")
        if (
            any(
                not text.strip() or len(text) > 2000
                for text in (self.original_text, self.transformed_text)
            )
            or not 1 <= len(self.method.strip()) <= 120
        ):
            raise ValueError("Text transformation exceeds its bounds")
        if not all(
            valid_language_code(value) for value in (self.source_language, self.target_language)
        ):
            raise ValueError("Invalid transformation language")
        validate_script(self.source_script)
        validate_script(self.target_script)
        if any(
            value is not None and not 1 <= len(value) <= 200
            for value in (self.model, self.provider)
        ):
            raise ValueError("Invalid transformation model provenance")
        if self.origin not in {"operator", "source", "machine"} or self.review_status not in {
            "unreviewed",
            "operator_declared",
        }:
            raise ValueError("Invalid transformation provenance")
        if len(self.limitations) > 4 or any(len(value) > 500 for value in self.limitations):
            raise ValueError("Transformation limitations exceed bounds")

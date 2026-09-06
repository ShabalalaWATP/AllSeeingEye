"""Strictly bounded synthetic casebooks, with reference labels kept outside model prompts."""

import hashlib
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.domain.events import Category, Event, Reliability, content_hash, event_id
from ase.domain.grading import SourceProfile, grade_events

CASE_DIRECTORY = Path(__file__).parent / "cases"
MAX_CASE_BYTES = 128_000


class CaseSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    organisation: str = Field(default="", max_length=80)
    instrument: bool = False
    flags: list[str] = Field(default_factory=list, max_length=10)


class CaseEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=80)
    source: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(default="", max_length=2000)
    language: str = Field(default="en", max_length=10)
    title_en: str | None = Field(default=None, max_length=300)
    published_at: datetime
    reliability: Reliability = Reliability.F


class ReferenceRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label_origin: str = "Assistant-authored synthetic fixture definitions"
    human_review_status: str = "pending"
    reference_facts: list[str] = Field(min_length=1, max_length=20)
    required_event_keys: list[str] = Field(default_factory=list, max_length=30)
    counterevidence_event_keys: list[str] = Field(default_factory=list, max_length=30)
    required_caveats: list[str] = Field(min_length=1, max_length=20)
    forbidden_inferences: list[str] = Field(min_length=1, max_length=20)
    expected_declared_organisation_groups: int | None = Field(default=None, ge=0)


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,79}$")
    title: str = Field(min_length=1, max_length=160)
    question: str = Field(min_length=1, max_length=1000)
    as_of: datetime
    window_hours: int = Field(default=48, ge=1, le=168)
    sources: list[CaseSource] = Field(max_length=30)
    events: list[CaseEvent] = Field(max_length=50)
    reference: ReferenceRubric

    @model_validator(mode="after")
    def consistent_labels(self) -> "EvaluationCase":
        keys = [event.key for event in self.events]
        if len(keys) != len(set(keys)):
            raise ValueError("Event keys must be unique within a case.")
        sources = [source.id for source in self.sources]
        if len(sources) != len(set(sources)):
            raise ValueError("Source ids must be unique within a case.")
        required = self.reference.required_event_keys + self.reference.counterevidence_event_keys
        if not set(required) <= set(keys):
            raise ValueError("Every reference event key must identify a case event.")
        if self.as_of.tzinfo is None or any(
            event.published_at.tzinfo is None for event in self.events
        ):
            raise ValueError("Case timestamps must include their timezone.")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()

    def source_profiles(self) -> dict[str, SourceProfile]:
        return {
            source.id: SourceProfile(
                source.id,
                source.organisation,
                source.name,
                source.instrument,
                frozenset(source.flags),
            )
            for source in self.sources
        }

    def event_ids(self, keys: list[str]) -> set[str]:
        return {event_id(event.source, event.key) for event in self.events if event.key in keys}

    def graded_events(self) -> list[Event]:
        events = [
            Event(
                id=event_id(item.source, item.key),
                source_id=item.source,
                category=Category.NEWS,
                subtype="evaluation_fixture",
                title=item.title,
                summary=item.summary,
                published_at=item.published_at,
                observed_at=self.as_of,
                reliability=item.reliability,
                language=item.language,
                title_en=item.title_en,
                url=f"https://example.invalid/{self.id}/{item.key}",
                content_hash=content_hash(item.title, item.summary),
            )
            for item in self.events
        ]
        return [graded.apply() for graded in grade_events(events, self.source_profiles())]


def load_cases(directory: Path = CASE_DIRECTORY) -> list[EvaluationCase]:
    paths = sorted(directory.glob("*.json"))
    if not paths or len(paths) > 100:
        raise ValueError("A casebook must contain between one and 100 JSON cases.")
    cases = []
    for path in paths:
        if path.stat().st_size > MAX_CASE_BYTES:
            raise ValueError("A case file exceeds the size limit.")
        cases.append(EvaluationCase.model_validate_json(path.read_bytes()))
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Case ids must be unique.")
    return cases

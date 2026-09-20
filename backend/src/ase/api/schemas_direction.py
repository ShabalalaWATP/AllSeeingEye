"""Request and response models for areas of interest and collection plans."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field

from ase.api.schemas_events import EventOut
from ase.api.schemas_research_area import ResearchAreaIn, ResearchAreaOut
from ase.application.direction.areas import AoiInput
from ase.application.direction.plans import PirInput, PlanEvidence, PlanInput, SirInput
from ase.domain.collection import AreaOfInterest, CollectionPlan, Pir, Sir
from ase.domain.events import Category


class AoiIn(BaseModel):
    team_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    kind: str = Field(pattern="^(bbox|countries|geometry)$")
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    countries: list[str] = Field(default_factory=list, max_length=30)

    research_area: ResearchAreaIn | None = None

    def to_input(self) -> AoiInput:
        box = tuple(self.bbox) if self.bbox else None
        return AoiInput(
            name=self.name,
            kind=self.kind,
            research_area=self.research_area.to_domain() if self.research_area else None,
            bbox=box,  # type: ignore[arg-type]
            countries=[code[:2] for code in self.countries],
            description=self.description,
            team_id=self.team_id,
        )


class AoiOut(BaseModel):
    research_area: ResearchAreaOut | None = None
    team_id: UUID | None
    id: UUID
    name: str
    description: str
    kind: str
    bbox: list[float] | None
    countries: list[str]
    created_by: UUID
    created_at: datetime

    @classmethod
    def from_area(cls, area: AreaOfInterest) -> Self:
        box = area.bbox
        return cls(
            id=area.id,
            name=area.name,
            description=area.description,
            kind=area.kind,
            research_area=ResearchAreaOut.model_validate(area.research_area)
            if area.research_area
            else None,
            bbox=[box.west, box.south, box.east, box.north] if box else None,
            countries=list(area.countries),
            created_by=area.created_by,
            created_at=area.created_at,
            team_id=area.team_id,
        )


class AoisOut(BaseModel):
    items: list[AoiOut]


class SirIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    categories: list[Category] = Field(default_factory=list, max_length=11)

    def to_input(self) -> SirInput:
        return SirInput(
            text=self.text, keywords=[k[:60] for k in self.keywords], categories=self.categories
        )


class PirIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    sirs: list[SirIn] = Field(default_factory=list, max_length=12)

    def to_input(self) -> PirInput:
        return PirInput(text=self.text, sirs=[sir.to_input() for sir in self.sirs])


class PlanIn(BaseModel):
    team_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    aoi_id: UUID | None = None
    countries: list[str] = Field(default_factory=list, max_length=30)
    pirs: list[PirIn] = Field(min_length=1, max_length=8)
    enabled: bool = True

    def to_input(self) -> PlanInput:
        return PlanInput(
            name=self.name,
            description=self.description,
            aoi_id=self.aoi_id,
            countries=[code[:2] for code in self.countries],
            pirs=[pir.to_input() for pir in self.pirs],
            enabled=self.enabled,
            team_id=self.team_id,
        )


class SirOut(BaseModel):
    code: str
    text: str
    keywords: list[str]
    categories: list[Category]

    @classmethod
    def from_sir(cls, sir: Sir) -> Self:
        return cls(
            code=sir.code,
            text=sir.text,
            keywords=list(sir.keywords),
            categories=list(sir.categories),
        )


class PirOut(BaseModel):
    code: str
    text: str
    sirs: list[SirOut]

    @classmethod
    def from_pir(cls, pir: Pir) -> Self:
        return cls(code=pir.code, text=pir.text, sirs=[SirOut.from_sir(sir) for sir in pir.sirs])


class PlanOut(BaseModel):
    team_id: UUID | None
    id: UUID
    name: str
    description: str
    aoi_id: UUID | None
    countries: list[str]
    pirs: list[PirOut]
    enabled: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_plan(cls, plan: CollectionPlan) -> Self:
        return cls(
            id=plan.id,
            name=plan.name,
            description=plan.description,
            aoi_id=plan.aoi_id,
            countries=list(plan.countries),
            pirs=[PirOut.from_pir(pir) for pir in plan.pirs],
            enabled=plan.enabled,
            created_by=plan.created_by,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            team_id=plan.team_id,
        )


class PlansOut(BaseModel):
    items: list[PlanOut]


class SirEvidenceOut(BaseModel):
    code: str
    text: str
    events: list[EventOut]


class PlanEvidenceOut(BaseModel):
    plan: PlanOut
    aoi: AoiOut | None
    considered: int
    sirs: list[SirEvidenceOut]

    @classmethod
    def from_evidence(cls, evidence: PlanEvidence) -> Self:
        return cls(
            plan=PlanOut.from_plan(evidence.plan),
            aoi=AoiOut.from_area(evidence.aoi) if evidence.aoi else None,
            considered=evidence.considered,
            sirs=[
                SirEvidenceOut(
                    code=sir.code,
                    text=sir.text,
                    events=[EventOut.from_event(event) for event in sir.events],
                )
                for sir in evidence.sirs
            ],
        )

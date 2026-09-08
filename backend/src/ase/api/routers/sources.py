"""Authenticated source context without operator URLs, credentials or health errors."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_source_ratings import SourceRatingOut
from ase.domain.events import Category, Reliability
from ase.domain.source_discovery import CoverageScope, source_coverage
from ase.domain.source_ratings import unassessed_source_rating
from ase.domain.sources import SourceKind

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceSummaryOut(BaseModel):
    id: str
    name: str
    organisation: str
    parent_organisation: str | None
    category: Category
    language: str
    reliability: Reliability
    rating: SourceRatingOut
    kind: SourceKind
    requires_key: bool
    collection_mode: Literal["on_demand", "scheduled"]
    coverage_scope: CoverageScope
    coverage_countries: list[str]
    coverage_regions: list[str]
    coverage_note: str


class SourcesOut(BaseModel):
    items: list[SourceSummaryOut]


@router.get("")
async def list_sources(user: CurrentUser, container: ContainerDep) -> SourcesOut:
    research_ids = {spec.id for spec in container.research_sources}
    specs = {spec.id: spec for spec in container.research_sources}
    specs.update({connector.spec.id: connector.spec for connector in container.connectors})
    return SourcesOut(
        items=[
            SourceSummaryOut(
                id=spec.id,
                name=spec.name,
                organisation=spec.organisation,
                parent_organisation=spec.parent_organisation,
                category=spec.category,
                language=spec.language,
                reliability=spec.reliability,
                rating=SourceRatingOut.model_validate(spec.rating or unassessed_source_rating()),
                kind=spec.kind,
                requires_key=spec.requires_key,
                collection_mode="on_demand" if spec.id in research_ids else "scheduled",
                coverage_scope=source_coverage(spec.id).scope,
                coverage_countries=list(source_coverage(spec.id).countries),
                coverage_regions=list(source_coverage(spec.id).regions),
                coverage_note=source_coverage(spec.id).note,
            )
            for spec in sorted(specs.values(), key=lambda item: (item.name.casefold(), item.id))
        ]
    )

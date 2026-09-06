"""Authenticated source context without operator URLs, credentials or health errors."""

from fastapi import APIRouter
from pydantic import BaseModel

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_source_ratings import SourceRatingOut
from ase.domain.events import Category, Reliability
from ase.domain.source_ratings import unassessed_source_rating

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


class SourcesOut(BaseModel):
    items: list[SourceSummaryOut]


@router.get("")
async def list_sources(user: CurrentUser, container: ContainerDep) -> SourcesOut:
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
            )
            for spec in sorted(specs.values(), key=lambda item: (item.name.casefold(), item.id))
        ]
    )

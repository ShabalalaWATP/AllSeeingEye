"""Explicit public company-name lookup. No drafts or identifiers are persisted."""

from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.session_fence import FenceDep
from ase.container.lei_candidates import lei_candidates

router = APIRouter(prefix="/research/lei-candidates", tags=["research"])


class LeiCandidatesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=200)
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")


class LeiCandidateOut(BaseModel):
    lei: str
    name: str
    jurisdiction: str
    status: str


class LeiCandidatesOut(BaseModel):
    items: list[LeiCandidateOut]


@router.post("")
async def find_lei_candidates(
    body: LeiCandidatesIn,
    user: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
    response: Response,
) -> LeiCandidatesOut:
    service = lei_candidates(container)
    rows = await service.search(user.id, body.name, body.country)
    result = LeiCandidatesOut(
        items=[
            LeiCandidateOut(
                lei=row.lei,
                name=row.name,
                jurisdiction=row.jurisdiction,
                status=row.status,
            )
            for row in rows
        ]
    )
    async with container.source_admission.guard():
        await service.require_enabled()
        await fence.confirm()
        response.headers["Cache-Control"] = "private, no-store"
        fence.assert_live()
        return result

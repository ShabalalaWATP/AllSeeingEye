"""The bearer account's private preferences, available to every active role."""

from fastapi import APIRouter, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, SessionDep
from ase.api.schemas_profile import ProfileOut, ProfileUpdateIn

router = APIRouter(prefix="/me/profile", tags=["me"])


@router.get("", response_model=ProfileOut)
async def get_profile(
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> ProfileOut:
    response.headers["Cache-Control"] = "no-store"
    return ProfileOut.model_validate(await container.profile(session).get(claims))


@router.patch("", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdateIn,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> ProfileOut:
    result = await container.profile(session).update(
        claims,
        body.model_dump(exclude_unset=True),
        context,
    )
    response.headers["Cache-Control"] = "no-store"
    return ProfileOut.model_validate(result)

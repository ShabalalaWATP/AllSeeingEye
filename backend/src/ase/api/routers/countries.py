"""Countries known to the resolver, for the nation filter and country panel."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from ase.api.catalogue_responses import catalogue_responses
from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_geo import CountriesOut, CountryOut
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/countries", tags=["geo"])


@router.get("", response_model=CountriesOut)
async def list_countries(
    user: CurrentUser, container: ContainerDep, request: Request, fence: FenceDep
) -> Response:
    snapshot = container.countries
    result = catalogue_responses.get(
        "/api/countries",
        snapshot,
        lambda: CountriesOut(items=[CountryOut.from_country(c) for c in snapshot.countries()]),
    )
    await fence.confirm()
    return result.response(request.headers.get("if-none-match"))

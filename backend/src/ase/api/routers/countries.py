"""Countries known to the resolver, for the nation filter and country panel."""

from __future__ import annotations

from fastapi import APIRouter

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_geo import CountriesOut, CountryOut

router = APIRouter(prefix="/countries", tags=["geo"])


@router.get("")
async def list_countries(user: CurrentUser, container: ContainerDep) -> CountriesOut:
    return CountriesOut(
        items=[CountryOut.from_country(country) for country in container.countries.countries()]
    )

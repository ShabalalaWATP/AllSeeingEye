"""Authenticated reference lookups for identifiers the map shows; bounded and read-only."""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.schemas_reference import ReferenceEntryOut, ReferenceLookupOut
from ase.api.session_guard import validate_request_session
from ase.domain.reference import MAX_LOOKUP_KEYS, ReferenceKind

router = APIRouter(prefix="/reference", tags=["reference"])
CAVEAT = (
    "A note describes the object publicly recorded under this identifier. Identifiers are "
    "reused, mistyped and spoofed, so a match is background, not confirmation of identity."
)


@router.get("")
async def lookup_reference(
    kind: ReferenceKind,
    keys: Annotated[str, Query(max_length=MAX_LOOKUP_KEYS * 33)],
    user: CurrentUser,
    claims: ClaimsDep,
    response: Response,
    container: ContainerDep,
) -> ReferenceLookupOut:
    catalogue = container.reference_catalogue
    wanted = tuple(key.strip() for key in keys.split(",") if key.strip())[:MAX_LOOKUP_KEYS]
    entries = catalogue.lookup(kind, wanted)
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return ReferenceLookupOut(
        items=[ReferenceEntryOut.from_entry(entry) for entry in entries],
        retrieved_at=catalogue.retrieved_at,
        caveat=CAVEAT,
    )

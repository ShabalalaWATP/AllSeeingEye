"""A source's track record across the caller's latest visible saved reports."""

from typing import Annotated

from fastapi import APIRouter, Path, Response

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_source_track_record import SourceTrackRecordOut
from ase.api.session_fence import FenceDep
from ase.container.source_track_record import source_track_record

router = APIRouter(prefix="/sources", tags=["sources"])
SourceId = Annotated[
    str, Path(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
]


@router.get("/{source_id}/track-record")
async def get_track_record(
    source_id: SourceId,
    user: CurrentUser,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> SourceTrackRecordOut:
    result = await source_track_record(container, session).read(user, source_id)
    response.headers["Cache-Control"] = "private, no-store"
    return await fence.release(SourceTrackRecordOut.model_validate(result), session=session)

"""Session-local source track record service; read only, no model or network work."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.source_track_record import SqlSourceTrackRecordReader
from ase.application.reports.source_track_record import SourceTrackRecordService

if TYPE_CHECKING:
    from ase.container import Container


def source_track_record(container: "Container", session: AsyncSession) -> SourceTrackRecordService:
    return SourceTrackRecordService(
        SqlSourceTrackRecordReader(session), container.access_policy(session)
    )

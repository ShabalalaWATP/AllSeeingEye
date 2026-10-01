"""On-demand source track record over the caller's latest visible saved reports."""

from ase.application.access import AccessPolicy
from ase.application.ports.source_track_record import SourceTrackRecordReader
from ase.domain.errors import InvalidRequest
from ase.domain.source_track_record import (
    MAX_REVIEW_SCAN,
    MAX_TRACK_RECORD_REPORTS,
    MAX_VERDICT_SCAN,
    SourceTrackRecord,
    build_track_record,
    valid_source_id,
)
from ase.domain.users import User


class SourceTrackRecordService:
    """Stores nothing. Authorisation is the caller's current report visibility."""

    def __init__(self, reader: SourceTrackRecordReader, access: AccessPolicy) -> None:
        self._reader = reader
        self._access = access

    async def read(self, actor: User, source_id: str) -> SourceTrackRecord:
        if not valid_source_id(source_id):
            raise InvalidRequest("Choose a catalogue source identifier.")
        visibility = (await self._access.context(actor)).visibility
        population = await self._reader.population(visibility, source_id, MAX_TRACK_RECORD_REPORTS)
        reviews = await self._reader.reviews(
            visibility, source_id, population.report_ids, MAX_REVIEW_SCAN
        )
        verdicts = await self._reader.verdicts(
            visibility,
            frozenset((row.report_id, row.version_number) for row in population.versions),
            MAX_VERDICT_SCAN,
        )
        return build_track_record(source_id, population, reviews, verdicts)

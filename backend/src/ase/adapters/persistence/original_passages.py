"""Scoped, hash-checked selected excerpts with physical expiry and report linking."""

import hashlib
import json
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import ReportVersionRow
from ase.adapters.persistence.original_passage_models import OriginalPassageRow as Row
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.application.research.original_frozen import (
    freeze_selected_original,
    frozen_original_from_dict,
)
from ase.application.research.original_passages import OriginalDocumentVersion
from ase.application.research.original_staging import StagedOriginalPassage

MAX_FROZEN_EXCERPT_BYTES = 80 * 1024


def _canonical(value: dict[str, object]) -> bytes:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    if len(encoded) > MAX_FROZEN_EXCERPT_BYTES:
        raise ValueError("Selected original excerpt exceeds its retention bound")
    return encoded


def _staged(row: Row) -> StagedOriginalPassage:
    encoded = _canonical(row.snapshot)
    if hashlib.sha256(encoded).hexdigest() != row.snapshot_sha256:
        raise ValueError("Retained original excerpt integrity failed")
    document = frozen_original_from_dict(row.snapshot)
    if (
        len(document.passages) != 1
        or document.owner_id != row.owner_id
        or document.team_id != row.team_id
        or document.source_id != row.source_id
        or document.candidate_id != row.candidate_id
        or document.id != row.document_version_id
        or document.passages[0].id != row.passage_id
        or document.expires_at != row.expires_at
    ):
        raise ValueError("Retained original excerpt provenance failed")
    return StagedOriginalPassage(
        row.id, row.job_id, row.event_id, row.evidence_label, document, row.expires_at
    )


class SqlOriginalPassageRepository:
    """No implicit commit. A staged excerpt is unreadable through a report until linked."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def stage(
        self,
        *,
        job_id: UUID,
        event_id: str,
        evidence_label: str,
        document: OriginalDocumentVersion,
    ) -> StagedOriginalPassage:
        if not document.passages or not 1 <= len(event_id) <= 256:
            raise ValueError("An exact selected original passage is required")
        frozen = freeze_selected_original(document, (document.passages[0].id,))
        selected = frozen_original_from_dict(frozen)
        encoded = _canonical(frozen)
        row = Row(
            id=uuid4(),
            job_id=job_id,
            report_version_id=None,
            owner_id=selected.owner_id,
            team_id=selected.team_id,
            source_id=selected.source_id,
            event_id=event_id,
            evidence_label=evidence_label,
            candidate_id=selected.candidate_id,
            document_version_id=selected.id,
            passage_id=selected.passages[0].id,
            snapshot=frozen,
            snapshot_sha256=hashlib.sha256(encoded).hexdigest(),
            created_at=selected.retrieved_at,
            expires_at=selected.expires_at,
        )
        self.session.add(row)
        await self.session.flush()
        return _staged(row)

    async def staged(
        self, job_id: UUID, event_id: str, now: datetime
    ) -> StagedOriginalPassage | None:
        row = await self.session.scalar(
            select(Row).where(
                Row.job_id == job_id,
                Row.event_id == event_id,
                Row.expires_at > now,
            )
        )
        return _staged(row) if row is not None else None

    async def linked(
        self, ref: UUID, version_id: UUID, now: datetime
    ) -> StagedOriginalPassage | None:
        row = await self.session.scalar(
            select(Row).where(
                Row.id == ref,
                Row.report_version_id == version_id,
                Row.expires_at > now,
            )
        )
        return _staged(row) if row is not None else None

    async def link(
        self,
        *,
        job_id: UUID,
        ref: UUID,
        version_id: UUID,
        owner_id: UUID,
        team_id: UUID | None,
        event_id: str,
        evidence_label: str,
        now: datetime,
    ) -> bool:
        result = await self.session.scalar(
            update(Row)
            .where(
                Row.id == ref,
                Row.job_id == job_id,
                Row.report_version_id.is_(None),
                Row.owner_id == owner_id,
                Row.team_id == team_id,
                Row.event_id == event_id,
                Row.evidence_label == evidence_label,
                Row.expires_at > now,
            )
            .values(report_version_id=version_id)
            .returning(Row.id)
        )
        return result == ref

    async def expire(self, now: datetime) -> None:
        await self.session.execute(delete(Row).where(Row.expires_at <= now))

    async def delete_for_report(self, report_id: UUID) -> None:
        """Remove linked and staged excerpts before SQLite deletes report versions."""
        version_ids = select(ReportVersionRow.id).where(ReportVersionRow.report_id == report_id)
        job_ids = select(ReportJobRow.id).where(ReportJobRow.report_id == report_id)
        await self.session.execute(
            delete(Row).where(or_(Row.report_version_id.in_(version_ids), Row.job_id.in_(job_ids)))
        )

    async def delete_for_job(self, job_id: UUID) -> None:
        """Remove staged excerpts on inactive-job discard, including SQLite FK-off."""
        exists = await self.session.scalar(select(Row.id).where(Row.job_id == job_id).limit(1))
        if exists is not None:
            await self.session.execute(delete(Row).where(Row.job_id == job_id))

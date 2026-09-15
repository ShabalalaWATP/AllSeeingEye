"""Atomic ledger entries with exact claim/report parents and optimistic append."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.claim_models import ClaimRevisionRow, ClaimRow
from ase.adapters.persistence.ledger_codec import decode_entry, encode_entry
from ase.adapters.persistence.ledger_models import ReportLedgerEntryRow, ReportLedgerHeadRow
from ase.adapters.persistence.models import ReportRow, ReportVersionRow
from ase.domain.forecast_decisions import ForecastDecision, ForecastLedger
from ase.domain.forecast_ledger import ForecastVersion, PassageReference
from ase.domain.indicator_ledger import IndicatorLedger, IndicatorReading, IndicatorVersion
from ase.domain.report_ledgers import (
    MAX_REPORT_LEDGER_ENTRIES,
    LedgerEntry,
    LedgerKind,
    ReportLedger,
    ReportLedgerAnchor,
)


def _entry_id(value: LedgerEntry) -> UUID:
    if isinstance(value, (ForecastVersion, IndicatorVersion)):
        return UUID(value.version_id)
    return UUID(value.id)


def _recorded_at(value: LedgerEntry) -> datetime:
    return (
        value.issued_at
        if isinstance(value, (ForecastVersion, IndicatorVersion))
        else value.recorded_at
    )


def _row(anchor: ReportLedgerAnchor, value: LedgerEntry, ordinal: int) -> ReportLedgerEntryRow:
    kind, payload, digest, size = encode_entry(value)
    return ReportLedgerEntryRow(
        id=_entry_id(value),
        ledger_id=anchor.id,
        ordinal=ordinal,
        entry_kind=kind,
        recorded_at=_recorded_at(value),
        payload=payload,
        payload_sha256=digest,
        payload_bytes=size,
    )


def _history(
    head: ReportLedgerHeadRow,
    versions: list[ForecastVersion | IndicatorVersion],
    decisions: list[ForecastDecision | IndicatorReading],
) -> ForecastLedger | IndicatorLedger:
    if head.kind == LedgerKind.FORECAST:
        if any(not isinstance(row, ForecastVersion) for row in versions) or any(
            not isinstance(row, ForecastDecision) for row in decisions
        ):
            raise ValueError("Forecast ledger contains a mismatched entry")
        forecast_history = ForecastLedger(tuple(versions), tuple(decisions))  # type: ignore[arg-type]
        if forecast_history.current_version.forecast_id != str(head.id):
            raise ValueError("Forecast identity does not match its head")
        return forecast_history
    if head.kind == LedgerKind.INDICATOR:
        if any(not isinstance(row, IndicatorVersion) for row in versions) or any(
            not isinstance(row, IndicatorReading) for row in decisions
        ):
            raise ValueError("Indicator ledger contains a mismatched entry")
        indicator_history = IndicatorLedger(tuple(versions), tuple(decisions))  # type: ignore[arg-type]
        if indicator_history.versions[-1].indicator_id != str(head.id):
            raise ValueError("Indicator identity does not match its head")
        return indicator_history
    raise ValueError("Unsupported retained ledger kind")


class SqlReportLedgerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_ids(
        self, report_version_id: UUID, limit: int, offset: int
    ) -> tuple[tuple[UUID, ...], int]:
        query = select(ReportLedgerHeadRow.id).where(
            ReportLedgerHeadRow.report_version_id == report_version_id
        )
        total = int(
            await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        )
        ids = tuple(
            await self.session.scalars(
                query.order_by(ReportLedgerHeadRow.created_at.desc(), ReportLedgerHeadRow.id)
                .offset(offset)
                .limit(limit)
            )
        )
        return ids, total

    async def get(self, ledger_id: UUID) -> ReportLedger | None:
        head = await self.session.get(ReportLedgerHeadRow, ledger_id, populate_existing=True)
        if head is None:
            return None
        rows = tuple(
            await self.session.scalars(
                select(ReportLedgerEntryRow)
                .where(ReportLedgerEntryRow.ledger_id == ledger_id)
                .order_by(ReportLedgerEntryRow.ordinal)
                .limit(MAX_REPORT_LEDGER_ENTRIES + 1)
                .execution_options(populate_existing=True)
            )
        )
        if not 1 <= head.latest_ordinal == len(rows) <= MAX_REPORT_LEDGER_ENTRIES:
            raise ValueError("Ledger head does not match retained entry count")
        versions: list[ForecastVersion | IndicatorVersion] = []
        decisions: list[ForecastDecision | IndicatorReading] = []
        for index, row in enumerate(rows, 1):
            value = decode_entry(row.entry_kind, row.payload, row.payload_sha256, row.payload_bytes)
            if (
                row.ordinal != index
                or row.id != _entry_id(value)
                or row.recorded_at != _recorded_at(value)
            ):
                raise ValueError("Ledger entry index does not match its saved content")
            if isinstance(value, (ForecastVersion, IndicatorVersion)):
                versions.append(value)
            else:
                decisions.append(value)
        history = _history(head, versions, decisions)
        if (head.kind == LedgerKind.INDICATOR) != (
            head.source_evidence_label is not None and head.source_excerpt_sha256 is not None
        ):
            raise ValueError("Ledger source anchor does not match its kind")
        source_reference = (
            PassageReference(
                str(head.report_version_id),
                head.source_evidence_label,
                head.source_excerpt_sha256,
            )
            if head.source_evidence_label is not None and head.source_excerpt_sha256 is not None
            else None
        )
        if isinstance(history, ForecastLedger):
            if history.versions[0].issued_at != head.created_at or any(
                version.claim_id != str(head.claim_id)
                or version.claim_version_id != str(head.claim_revision_id)
                or version.report_version_id != str(head.report_version_id)
                or any(
                    ref.report_version_id != str(head.report_version_id)
                    for ref in (*version.supporting, *version.contrary)
                )
                for version in history.versions
            ):
                raise ValueError("Forecast payload does not match its ledger anchor")
        elif history.versions[0].issued_at != head.created_at or any(
            version.source_reference != source_reference for version in history.versions
        ):
            raise ValueError("Indicator payload does not match its ledger anchor")
        anchor = ReportLedgerAnchor(
            head.id,
            LedgerKind(head.kind),
            head.report_id,
            head.report_version_id,
            head.claim_id,
            head.claim_revision_id,
            head.owner_id,
            head.team_id,
            head.created_at,
            head.latest_ordinal,
            source_reference,
        )
        return ReportLedger(anchor, history)

    async def create(self, anchor: ReportLedgerAnchor, first: LedgerEntry) -> bool:
        if anchor.latest_ordinal != 1 or not isinstance(first, (ForecastVersion, IndicatorVersion)):
            raise ValueError("A ledger starts with one immutable version")
        if (anchor.kind is LedgerKind.FORECAST) != isinstance(first, ForecastVersion):
            raise ValueError("Initial version does not match ledger kind")
        if (anchor.kind is LedgerKind.INDICATOR) != (anchor.source_reference is not None):
            raise ValueError("Indicator ledgers require an exact source excerpt reference")
        parent = await self.session.scalar(
            select(ClaimRow.id)
            .join(ReportRow, ReportRow.id == ClaimRow.report_id)
            .join(ReportVersionRow, ReportVersionRow.id == ClaimRow.report_version_id)
            .join(ClaimRevisionRow, ClaimRevisionRow.claim_id == ClaimRow.id)
            .where(
                ClaimRow.id == anchor.claim_id,
                ClaimRow.report_id == anchor.report_id,
                ClaimRow.report_version_id == anchor.report_version_id,
                ClaimRevisionRow.id == anchor.claim_revision_id,
                ReportVersionRow.report_id == anchor.report_id,
                ClaimRow.created_by == anchor.owner_id,
                ClaimRow.team_id == anchor.team_id,
                ReportRow.team_id == anchor.team_id,
            )
        )
        if parent is None:
            raise ValueError("Ledger requires an exact claim revision and report scope")
        try:
            async with self.session.begin_nested():
                self.session.add(
                    ReportLedgerHeadRow(
                        id=anchor.id,
                        kind=anchor.kind.value,
                        report_id=anchor.report_id,
                        report_version_id=anchor.report_version_id,
                        claim_id=anchor.claim_id,
                        claim_revision_id=anchor.claim_revision_id,
                        owner_id=anchor.owner_id,
                        team_id=anchor.team_id,
                        source_evidence_label=(
                            anchor.source_reference.evidence_id if anchor.source_reference else None
                        ),
                        source_excerpt_sha256=(
                            anchor.source_reference.passage_id if anchor.source_reference else None
                        ),
                        latest_ordinal=1,
                        created_at=anchor.created_at,
                    )
                )
                self.session.add(_row(anchor, first, 1))
                await self.session.flush()
        except IntegrityError:
            return False
        return True

    async def append(self, anchor: ReportLedgerAnchor, entry: LedgerEntry) -> bool:
        if anchor.latest_ordinal >= MAX_REPORT_LEDGER_ENTRIES:
            raise ValueError("This ledger reached its retained entry limit")
        try:
            async with self.session.begin_nested():
                changed = await self.session.scalar(
                    update(ReportLedgerHeadRow)
                    .where(
                        ReportLedgerHeadRow.id == anchor.id,
                        ReportLedgerHeadRow.latest_ordinal == anchor.latest_ordinal,
                    )
                    .values(latest_ordinal=anchor.latest_ordinal + 1)
                    .returning(ReportLedgerHeadRow.id)
                    .execution_options(synchronize_session=False)
                )
                if changed is None:
                    return False
                self.session.add(_row(anchor, entry, anchor.latest_ordinal + 1))
                await self.session.flush()
        except IntegrityError:
            return False
        return True


async def delete_report_ledgers(session: AsyncSession, report_id: UUID) -> None:
    """SQLite FK-off parity when the owning report is physically removed."""
    ids = select(ReportLedgerHeadRow.id).where(ReportLedgerHeadRow.report_id == report_id)
    await session.execute(
        delete(ReportLedgerEntryRow).where(ReportLedgerEntryRow.ledger_id.in_(ids))
    )
    await session.execute(
        delete(ReportLedgerHeadRow).where(ReportLedgerHeadRow.report_id == report_id)
    )

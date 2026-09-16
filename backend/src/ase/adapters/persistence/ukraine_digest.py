"""The small bounded history of Ukraine digests: the assessment and its provenance only.

Prompts and full evidence windows are never stored. Each row keeps the digest payload and
the citations that digest named, so a reader can see what it was written from.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, Integer, String, delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.domain.ukraine.digest import (
    MAX_CITATIONS,
    MAX_SOURCE_IDS,
    DigestCitation,
    StoredDigest,
    UkraineDigest,
)


class UkraineDigestRow(Base):
    __tablename__ = "ukraine_digests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    model: Mapped[str] = mapped_column(String(2048))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    source_ids: Mapped[list[str]] = mapped_column(JSON)
    evidence_items: Mapped[int] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)


def _citation(raw: dict[str, Any]) -> DigestCitation:
    dated = raw.get("dated_on")
    return DigestCitation(
        id=str(raw["id"]),
        kind=str(raw["kind"]),
        source_id=str(raw["source_id"]),
        label=str(raw["label"]),
        dated_on=date.fromisoformat(dated) if isinstance(dated, str) else None,
        url=raw["url"] if isinstance(raw.get("url"), str) else None,
    )


def _to_domain(row: UkraineDigestRow) -> StoredDigest:
    return StoredDigest(
        period_start=row.period_start,
        period_end=row.period_end,
        generated_at=row.generated_at,
        model=row.model,
        digest=UkraineDigest.model_validate(row.payload),
        citations=tuple(_citation(item) for item in row.citations[:MAX_CITATIONS]),
        source_ids=tuple(str(item) for item in row.source_ids[:MAX_SOURCE_IDS]),
        evidence_items=row.evidence_items,
        prompt_tokens=row.prompt_tokens,
        completion_tokens=row.completion_tokens,
    )


class SqlUkraineDigestStore:
    """Opens its own short sessions; generation is not inside a request unit of work."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def recent(self, limit: int) -> list[StoredDigest]:
        async with self._sessions() as session:
            rows = await session.scalars(
                select(UkraineDigestRow)
                .order_by(UkraineDigestRow.generated_at.desc(), UkraineDigestRow.id.desc())
                .limit(limit)
            )
            return [_to_domain(row) for row in rows]

    async def save(self, digest: StoredDigest, keep: int) -> None:
        async with self._sessions() as session:
            session.add(
                UkraineDigestRow(
                    period_start=digest.period_start,
                    period_end=digest.period_end,
                    generated_at=digest.generated_at,
                    model=digest.model[:2048],
                    payload=digest.digest.model_dump(mode="json", by_alias=True),
                    citations=[
                        {
                            "id": item.id,
                            "kind": item.kind,
                            "source_id": item.source_id,
                            "label": item.label,
                            "dated_on": item.dated_on.isoformat() if item.dated_on else None,
                            "url": item.url,
                        }
                        for item in digest.citations[:MAX_CITATIONS]
                    ],
                    source_ids=list(digest.source_ids[:MAX_SOURCE_IDS]),
                    evidence_items=digest.evidence_items,
                    prompt_tokens=digest.prompt_tokens,
                    completion_tokens=digest.completion_tokens,
                )
            )
            await session.flush()
            kept = (
                select(UkraineDigestRow.id)
                .order_by(UkraineDigestRow.generated_at.desc(), UkraineDigestRow.id.desc())
                .limit(keep)
                .scalar_subquery()
            )
            await session.execute(delete(UkraineDigestRow).where(UkraineDigestRow.id.not_in(kept)))
            await session.commit()

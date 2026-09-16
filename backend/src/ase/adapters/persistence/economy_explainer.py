"""Read and replace the cached explainer, keeping only the newest retained rows."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.economy_explainer_models import EconomyExplainerRow
from ase.domain.economy_explainer import (
    RETAINED_ROWS,
    StoredExplainer,
    from_payload,
    to_payload,
)


class SqlEconomyExplainerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest(self) -> StoredExplainer | None:
        row = await self._session.scalar(
            select(EconomyExplainerRow)
            .order_by(EconomyExplainerRow.generated_at.desc(), EconomyExplainerRow.id.desc())
            .limit(1)
        )
        if row is None:
            return None
        try:
            text = from_payload(row.payload)
        except (ValueError, TypeError):
            # A row written by an older or damaged payload shape is treated as absent.
            return None
        return StoredExplainer(
            fingerprint=row.fingerprint,
            window_start=row.window_start,
            text=text,
            model=row.model,
            generated_at=row.generated_at,
            snapshot_fetched_at=row.snapshot_fetched_at,
            prompt_tokens=row.prompt_tokens,
            completion_tokens=row.completion_tokens,
        )

    async def save(self, explainer: StoredExplainer) -> None:
        self._session.add(
            EconomyExplainerRow(
                fingerprint=explainer.fingerprint,
                window_start=explainer.window_start,
                payload=to_payload(explainer.text),
                model=explainer.model,
                generated_at=explainer.generated_at,
                snapshot_fetched_at=explainer.snapshot_fetched_at,
                prompt_tokens=explainer.prompt_tokens,
                completion_tokens=explainer.completion_tokens,
            )
        )
        await self._session.flush()
        keep = list(
            await self._session.scalars(
                select(EconomyExplainerRow.id)
                .order_by(EconomyExplainerRow.generated_at.desc(), EconomyExplainerRow.id.desc())
                .limit(RETAINED_ROWS)
            )
        )
        await self._session.execute(
            delete(EconomyExplainerRow).where(EconomyExplainerRow.id.notin_(keep))
        )
        await self._session.flush()

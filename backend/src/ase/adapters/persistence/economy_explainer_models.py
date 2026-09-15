"""A small operational aggregate: the latest cached economy explainer text.

Only generated text, its provenance and its token counts are stored. Prompts, fact packs
and raw public events are never persisted, and at most two rows are retained.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class EconomyExplainerRow(Base):
    __tablename__ = "economy_explainers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    window_start: Mapped[datetime] = mapped_column(UTCDateTime)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    model: Mapped[str] = mapped_column(String(255))
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    snapshot_fetched_at: Mapped[datetime] = mapped_column(UTCDateTime)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

"""SQL rows for each account's in-app bell preferences (migration 0080).

Small configuration only: one preference row per account and at most
``MAX_RULE_MUTES`` mutes per account, removed with the account or the rule.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class BellPreferenceRow(Base):
    __tablename__ = "bell_preferences"

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_bell_preferences_user"),
        primary_key=True,
    )
    muted_kinds: Mapped[list[Any]] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class BellRuleMuteRow(Base):
    __tablename__ = "bell_rule_mutes"
    __table_args__ = (Index("ix_bell_rule_mutes_indicator", "indicator_id"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_bell_rule_mutes_user"),
        primary_key=True,
    )
    indicator_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("indicators.id", ondelete="CASCADE", name="fk_bell_rule_mutes_rule"),
        primary_key=True,
    )
    muted_at: Mapped[datetime] = mapped_column(UTCDateTime)

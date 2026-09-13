"""Private, explicitly saved Ask Eye conversation snapshots."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class AssistantConversationRow(Base):
    __tablename__ = "assistant_conversations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120))
    transcript: Mapped[str] = mapped_column(Text)
    transcript_bytes: Mapped[int] = mapped_column(Integer)
    turn_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)

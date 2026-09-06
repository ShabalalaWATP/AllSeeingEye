"""Only hashes of high-entropy recovery codes are persisted."""

from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base


class RecoveryCodeRow(Base):
    __tablename__ = "mfa_recovery_codes"
    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    security_version: Mapped[int] = mapped_column(Integer)

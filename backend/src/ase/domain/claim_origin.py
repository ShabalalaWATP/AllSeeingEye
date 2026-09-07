"""Immutable provenance for the model attempt that first proposed an assertion."""

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ase.domain.llm import MAX_MODEL_ID_LENGTH


@dataclass(frozen=True, slots=True)
class ClaimModelOrigin:
    batch_id: UUID
    profile_id: UUID
    profile_revision: int
    provider: str
    requested_model: str
    returned_model: str
    input_sha256: str
    method_version: str
    generated_at: datetime

    def validate(self) -> None:
        if not isinstance(self.batch_id, UUID) or not isinstance(self.profile_id, UUID):
            raise ValueError("Invalid claim model identity")
        if type(self.profile_revision) is not int or self.profile_revision < 1:
            raise ValueError("Invalid claim model profile revision")
        if not isinstance(self.generated_at, datetime) or self.generated_at.utcoffset() is None:
            raise ValueError("Claim model time must be timezone-aware")
        for text, limit in (
            (self.provider, 256),
            (self.requested_model, MAX_MODEL_ID_LENGTH),
            (self.returned_model, MAX_MODEL_ID_LENGTH),
            (self.method_version, 256),
        ):
            if not isinstance(text, str) or not text.strip() or len(text) > limit:
                raise ValueError("Invalid claim model provenance text")
            text.encode("utf-8")
            if any(ord(char) < 32 for char in text):
                raise ValueError("Invalid claim model provenance control text")
        if (
            not isinstance(self.input_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", self.input_sha256) is None
        ):
            raise ValueError("Invalid claim model input digest")

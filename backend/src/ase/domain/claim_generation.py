"""Versioned outcome of automatic claim generation, independent of later annotations."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from ase.domain.claim_origin import ClaimModelOrigin


class ClaimGenerationStatus(StrEnum):
    COMPLETED = "completed"
    EMPTY = "empty"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    NO_MODEL = "no_model"
    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"


@dataclass(frozen=True, slots=True)
class ClaimGenerationReceipt:
    """Exact initial revisions allow later exports to distinguish operator corrections.

    Absence on a legacy report means not recorded, never a successful empty result.
    The receipt contains no prompt, credential or provider error text.
    """

    status: ClaimGenerationStatus
    revision_ids: tuple[UUID, ...] = ()
    model_origin: ClaimModelOrigin | None = None
    schema_version: int = 1

    def validate(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("Unsupported claim generation receipt version")
        if not isinstance(self.status, ClaimGenerationStatus):
            raise ValueError("Invalid claim generation status")
        if (
            not isinstance(self.revision_ids, tuple)
            or len(self.revision_ids) > 20
            or any(not isinstance(value, UUID) for value in self.revision_ids)
            or len(set(self.revision_ids)) != len(self.revision_ids)
        ):
            raise ValueError("Invalid generated claim revision identities")
        if self.model_origin is not None:
            self.model_origin.validate()
        if self.status is ClaimGenerationStatus.COMPLETED:
            if not self.revision_ids or self.model_origin is None:
                raise ValueError("Completed claim generation needs revisions and provenance")
        elif self.revision_ids:
            raise ValueError("Unsuccessful claim generation cannot reference saved revisions")
        if (
            self.status
            in (
                ClaimGenerationStatus.NO_MODEL,
                ClaimGenerationStatus.RATE_LIMITED,
                ClaimGenerationStatus.UNSUPPORTED,
            )
            and self.model_origin is not None
        ):
            raise ValueError("Unattempted generation cannot claim model provenance")


def claim_generation_to_dict(value: ClaimGenerationReceipt) -> dict[str, Any]:
    value.validate()
    origin = value.model_origin
    return {
        "schema_version": value.schema_version,
        "status": value.status.value,
        "revision_ids": [str(item) for item in value.revision_ids],
        "model_origin": None
        if origin is None
        else {
            "batch_id": str(origin.batch_id),
            "profile_id": str(origin.profile_id),
            "profile_revision": origin.profile_revision,
            "provider": origin.provider,
            "requested_model": origin.requested_model,
            "returned_model": origin.returned_model,
            "input_sha256": origin.input_sha256,
            "method_version": origin.method_version,
            "generated_at": origin.generated_at.isoformat(),
        },
    }


def claim_generation_from_dict(data: Mapping[str, Any]) -> ClaimGenerationReceipt:
    if set(data) != {"schema_version", "status", "revision_ids", "model_origin"}:
        raise ValueError("Invalid claim generation receipt fields")
    ids = data["revision_ids"]
    if not isinstance(ids, list) or len(ids) > 20:
        raise ValueError("Invalid generated claim revisions")
    if any(not isinstance(item, str) for item in ids):
        raise ValueError("Invalid generated claim revision identity")
    raw = data["model_origin"]
    origin = None
    if raw is not None:
        if not isinstance(raw, dict) or set(raw) != {
            "batch_id",
            "profile_id",
            "profile_revision",
            "provider",
            "requested_model",
            "returned_model",
            "input_sha256",
            "method_version",
            "generated_at",
        }:
            raise ValueError("Invalid claim generation provenance fields")
        if any(not isinstance(raw[key], str) for key in ("batch_id", "profile_id", "generated_at")):
            raise ValueError("Invalid claim generation provenance identity or time")
        origin = ClaimModelOrigin(
            UUID(raw["batch_id"]),
            UUID(raw["profile_id"]),
            raw["profile_revision"],
            raw["provider"],
            raw["requested_model"],
            raw["returned_model"],
            raw["input_sha256"],
            raw["method_version"],
            datetime.fromisoformat(raw["generated_at"]),
        )
    value = ClaimGenerationReceipt(
        ClaimGenerationStatus(data["status"]),
        tuple(UUID(item) for item in ids),
        origin,
        data["schema_version"],
    )
    value.validate()
    return value

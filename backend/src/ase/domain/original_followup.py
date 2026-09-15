"""Bounded public-original follow-through receipts, without retained passage text."""

import re
from dataclasses import asdict, dataclass
from typing import Any, Literal
from uuid import UUID

MAX_ORIGINAL_RECEIPTS = 10
OriginalStatus = Literal["acquired", "headline_only", "unavailable"]
REASONS = frozenset(
    {
        "original_passage_staged",
        "no_reviewed_policy",
        "requirement_mapping_unavailable",
        "source_not_admitted",
        "source_disabled",
        "policy_or_destination_not_permitted",
        "guarded_transport_unavailable",
        "insufficient_remaining_allowance",
        "source_phase_budget_exhausted",
        "source_operation_unknown",
        "fetch_timeout",
        "parser_timeout",
        "fetch_rejected",
        "parser_rejected",
        "source_disabled_after_acquisition",
        "policy_expired_after_acquisition",
        "parser_provenance_mismatch",
        "request_not_permitted",
        "destination_not_permitted",
        "source_admission_failed",
        "source_rate_or_terms_not_permitted",
        "redirect_limit",
        "http_status_not_permitted",
        "compressed_response_not_permitted",
        "body_limit_or_size_mismatch",
        "unsupported_media_type",
        "transport_receipt_invalid",
        "transport_failed",
        "original_candidate_unavailable",
        "retention_store_unavailable",
    }
)


@dataclass(frozen=True, slots=True)
class OriginalFollowupReceipt:
    evidence_label: str
    event_id: str
    source_id: str
    status: OriginalStatus
    reason: str
    candidate_id: str | None = None
    passage_ref: UUID | None = None
    passage_id: str | None = None
    document_version_id: str | None = None
    transport_requests: int | None = 0
    transport_requests_reserved: int = 0

    def __post_init__(self) -> None:
        if (
            not re.fullmatch(r"E[1-9][0-9]{0,2}", self.evidence_label)
            or not 1 <= len(self.event_id) <= 256
            or not 1 <= len(self.source_id) <= 120
            or self.status not in {"acquired", "headline_only", "unavailable"}
            or self.reason not in REASONS
            or (
                self.candidate_id is not None
                and not re.fullmatch(r"[0-9a-f]{64}", self.candidate_id)
            )
            or (self.passage_id is not None and not re.fullmatch(r"[0-9a-f]{64}", self.passage_id))
            or (
                self.document_version_id is not None
                and not re.fullmatch(r"[0-9a-f]{64}", self.document_version_id)
            )
            or (
                self.transport_requests is not None
                and (
                    type(self.transport_requests) is not int
                    or not 0 <= self.transport_requests <= 3
                )
            )
            or type(self.transport_requests_reserved) is not int
            or not 0 <= self.transport_requests_reserved <= 3
            or (self.status == "acquired")
            != (
                self.passage_ref is not None
                and self.passage_id is not None
                and self.document_version_id is not None
            )
        ):
            raise ValueError("Invalid original follow-through receipt")


def original_receipt_to_dict(value: OriginalFollowupReceipt) -> dict[str, Any]:
    result = asdict(value)
    result["passage_ref"] = str(value.passage_ref) if value.passage_ref else None
    return result


def original_receipt_from_dict(value: object) -> OriginalFollowupReceipt:
    if type(value) is not dict or set(value) != set(OriginalFollowupReceipt.__dataclass_fields__):
        raise ValueError("Invalid frozen original follow-through receipt")
    copied = dict(value)
    try:
        copied["passage_ref"] = UUID(copied["passage_ref"]) if copied["passage_ref"] else None
        receipt = OriginalFollowupReceipt(**copied)
    except (TypeError, ValueError, AttributeError):
        raise ValueError("Invalid frozen original follow-through receipt") from None
    if original_receipt_to_dict(receipt) != value:
        raise ValueError("Invalid frozen original follow-through receipt")
    return receipt

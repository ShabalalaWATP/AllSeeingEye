"""Validate retained typed manifests and independent storage integrity before use."""

import hashlib
import json
from dataclasses import asdict

from pydantic import TypeAdapter, ValidationError

from ase.application.reports.comparison_manifest import MAX_COMPARISON_BYTES, comparison_digest
from ase.domain.annotation_comparison import AnnotationComparison
from ase.domain.annotation_monitoring import AnnotationTransition
from ase.domain.errors import Conflict

_ADAPTER = TypeAdapter(AnnotationComparison)


def checked_payload(payload: str, digest: str, size: int) -> bytes:
    result = payload.encode("utf-8")
    if (
        len(result) != size
        or size > MAX_COMPARISON_BYTES
        or hashlib.sha256(result).hexdigest() != digest
    ):
        raise Conflict("The retained monitor manifest is unavailable or inconsistent.")
    return result


class StoredComparisonCodec:
    def decode(self, payload: bytes) -> AnnotationComparison:
        if len(payload) > MAX_COMPARISON_BYTES:
            raise Conflict("The retained monitor manifest is oversized.")
        try:
            value = _ADAPTER.validate_json(payload)
        except ValidationError as exc:
            raise Conflict("The retained monitor manifest is inconsistent.") from exc
        if comparison_digest(value) != value.comparison_sha256:
            raise Conflict("The retained comparison digest is inconsistent.")
        return value


def transition_hash(value: AnnotationTransition, payload: bytes) -> str:
    metadata = json.dumps(asdict(value), sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(metadata + b"\n" + payload).hexdigest()


def checked_transition(value: AnnotationTransition, payload: str, digest: str, size: int) -> bytes:
    data = payload.encode("utf-8")
    if len(data) != size or size > MAX_COMPARISON_BYTES or transition_hash(value, data) != digest:
        raise Conflict("The retained transition metadata or payload is inconsistent.")
    return data

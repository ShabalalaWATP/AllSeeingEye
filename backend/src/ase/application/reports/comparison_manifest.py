"""Bounded deterministic comparison manifests; digests cover policy and results."""

import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from uuid import UUID

from ase.domain.annotation_comparison import AnnotationComparison
from ase.domain.errors import InvalidRequest

MAX_COMPARISON_BYTES = 8 * 1024 * 1024


def _convert(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return str(value.value)
    raise TypeError("Unsupported comparison content")


def comparison_json(value: AnnotationComparison, *, for_digest: bool = False) -> bytes:
    payload = asdict(value)
    if for_digest:
        payload.pop("generated_at")
        payload.pop("comparison_sha256")
    result = bytearray()
    try:
        for part in json.JSONEncoder(
            default=_convert,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).iterencode(payload):
            encoded = part.encode("utf-8")
            if len(encoded) + len(result) > MAX_COMPARISON_BYTES:
                raise InvalidRequest(
                    "Comparison exceeds its 8 MiB manifest limit. Select fewer annotations."
                )
            result.extend(encoded)
    except (ValueError, TypeError, RecursionError) as exc:
        raise InvalidRequest("Comparison content cannot be safely exported.") from exc
    return bytes(result)


def comparison_digest(value: AnnotationComparison) -> str:
    return hashlib.sha256(comparison_json(value, for_digest=True)).hexdigest()

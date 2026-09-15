"""Bounded, versioned snapshots of saved subscription requests."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from ase.domain.report_jobs import canonical_job_payload

MAX_SNAPSHOT_BYTES = 65_536
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def canonical_snapshot(value: dict[str, Any]) -> str:  # noqa: PLR0912
    required = {
        "schema_version",
        "template_id",
        "scope",
        "request",
        "recurrence",
        "collection_policy",
        "avoid_repetition",
    }
    version = value.get("schema_version")
    if version not in (1, 2, 3, 4) or set(value) != (
        required
        | ({"subscription_context"} if version in (2, 3, 4) else set())
        | ({"brief_ref"} if version == 4 else set())
    ):
        raise ValueError("Invalid subscription request snapshot fields.")
    if value["collection_policy"] not in {"rolling_snapshot_v1", "since_last_success_v1"}:
        raise ValueError("Unsupported subscription request snapshot version or policy.")
    if version < 3 and value["collection_policy"] != "rolling_snapshot_v1":
        raise ValueError("Old subscription snapshots require their original policy.")
    if (
        type(value["template_id"]) is not str
        or type(value["scope"]) is not dict
        or type(value["request"]) is not dict
        or type(value["recurrence"]) is not dict
        or type(value["avoid_repetition"]) is not bool
    ):
        raise ValueError("Invalid subscription request snapshot shape.")
    if version in (3, 4):
        from ase.domain.subscription_recurrence import LocalRecurrence  # noqa: PLC0415

        recurrence = value["recurrence"]
        if set(recurrence) != {
            "timezone",
            "local_hour",
            "local_minute",
            "cadence",
            "weekday",
            "monthday",
            "anchor_month",
        }:
            raise ValueError("Invalid local subscription recurrence fields.")
        LocalRecurrence(
            recurrence["timezone"],
            recurrence["local_hour"],
            recurrence["local_minute"],
            recurrence["cadence"],
            recurrence["weekday"],
            recurrence["monthday"],
            recurrence["anchor_month"],
        )
    if version == 4:
        reference = value["brief_ref"]
        if type(reference) is not dict or set(reference) != {
            "id",
            "revision",
            "parent_report_id",
            "parent_version",
        }:
            raise ValueError("Invalid frozen Research Brief reference.")
        try:
            UUID(reference["id"])
            if type(reference["revision"]) is not int or reference["revision"] < 1:
                raise ValueError("Invalid Research Brief revision")
            if (reference["parent_report_id"] is None) != (reference["parent_version"] is None):
                raise ValueError("Invalid parent report reference")
            if reference["parent_report_id"] is not None:
                UUID(reference["parent_report_id"])
                if type(reference["parent_version"]) is not int or reference["parent_version"] < 1:
                    raise ValueError("Invalid parent report version")
        except (TypeError, ValueError, AttributeError) as exc:
            raise ValueError("Invalid frozen Research Brief reference.") from exc
    if version in (2, 3, 4):
        context = value["subscription_context"]
        if type(context) is not dict or set(context) != {"report_id", "seen_signatures"}:
            raise ValueError("Invalid subscription comparison context.")
        if context["report_id"] is not None:
            try:
                UUID(context["report_id"])
            except (TypeError, ValueError, AttributeError) as exc:
                raise ValueError("Invalid subscription baseline reference.") from exc
        signatures = context["seen_signatures"]
        if (
            type(signatures) is not list
            or len(signatures) > 500
            or any(type(item) is not str or not _DIGEST.fullmatch(item) for item in signatures)
            or len(set(signatures)) != len(signatures)
        ):
            raise ValueError("Invalid subscription content fingerprints.")
    # Reuse the bounded secret-field/tree checks while retaining this adapter's
    # independent schema version from the outer report-job checkpoint.
    canonical_job_payload({**value, "schema_version": 1})
    encoded = json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if len(encoded) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Subscription request snapshot is too large.")
    return encoded.decode("utf-8")


def decode_snapshot(value: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value)
        if type(decoded) is not dict or canonical_snapshot(decoded) != value:
            raise ValueError("Invalid subscription request snapshot encoding.")
        return decoded
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("The retained subscription request snapshot is unavailable.") from exc

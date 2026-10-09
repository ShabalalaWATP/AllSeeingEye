"""Strict structural checks for the packaged rights register (no legal inference)."""

from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

TEXT = {"type": "string", "minLength": 1}
DATE = {"type": "string", "format": "date"}
URL = {"type": "string", "format": "uri", "pattern": "^https?://"}
RIGHTS = {"enum": ["unknown", "conditional", "permission_required"]}


def record(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def array(item: dict[str, Any]) -> dict[str, Any]:
    return {"type": "array", "items": item, "uniqueItems": True}


POLICY = record(
    {
        "name": TEXT,
        "terms_url": {"anyOf": [URL, {"type": "null"}]},
        "additional_terms_urls": array(URL),
        "licence": TEXT,
        "review_status": {
            "enum": [
                "terms_checked",
                "partial_review",
                "lookup_blocked",
                "lookup_inconclusive",
                "not_reviewed",
                "per_item_required",
            ]
        },
        "terms_checked_on": {"anyOf": [DATE, {"type": "null"}]},
        "lookup_attempted_on": {"anyOf": [DATE, {"type": "null"}]},
        "commercial_use": RIGHTS,
        "commercial_use_policy": {"enum": ["allowed", "forbidden", "licence_required"]},
        "hosted_multi_user_use": RIGHTS,
        "attribution": TEXT,
        "redistribution": TEXT,
        "risk": {"enum": ["low", "medium", "high"]},
        "actions": {
            **array(
                {"enum": ["keep", "attribute", "request_permission", "replace", "legal_review"]}
            ),
            "minItems": 1,
        },
        "notes": TEXT,
    }
)
POLICIES = record(
    {
        "schema_version": {"const": 1},
        "assessed_on": DATE,
        "policies": {"type": "object", "minProperties": 1, "additionalProperties": POLICY},
    }
)
SOURCE = record(
    {
        "id": TEXT,
        "name": TEXT,
        "family": TEXT,
        "policy": TEXT,
        "additional_policies": array(TEXT),
        "commercial_use": {"enum": ["allowed", "forbidden", "licence_required"]},
        "attribution_required": {"type": "boolean"},
        "licence_ref": TEXT,
        "source_url": {"anyOf": [URL, {"type": "null"}]},
        "source_url_kind": {
            "enum": ["publisher_or_provider", "catalogue_provenance_only", "per_item_provenance"]
        },
        "code_checked_on": DATE,
        "current_default": {
            "enum": [
                "scheduled",
                "on_demand",
                "off_until_configured",
                "off_until_selected",
                "available_asset",
                "initial_hybrid_basemap",
                "initial_hybrid_labels",
            ]
        },
        "gating_flags": array(TEXT),
        "upstream_licence_note": {"type": "string"},
        "source_specific_action": TEXT,
    }
)
REGISTER = record(
    {
        "schema_version": {"const": 1},
        "assessed_on": DATE,
        "source_revision": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
        "enforcement": {"const": "commercial_mode_opt_in"},
        "sources": {**array(SOURCE), "minItems": 1},
        "supplementary_sources": array(
            record(
                {
                    "id": TEXT,
                    "policy": TEXT,
                    "status": {"const": "not_in_current_backend_catalogue"},
                }
            )
        ),
        "camera_hosts": array(
            record(
                {
                    "host": {"type": "string", "pattern": r"^[a-z0-9.*-]+$"},
                    "uses": {**array({"enum": ["media", "frames"]}), "minItems": 1},
                    "policy": TEXT,
                    "provider_policy": {"anyOf": [TEXT, {"type": "null"}]},
                }
            )
        ),
    }
)


def validate_register(register: dict[str, Any], policy_document: dict[str, Any]) -> None:
    """Reject malformed, unlinked or falsely verified rights records."""
    for schema, instance in ((REGISTER, register), (POLICIES, policy_document)):
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)
    policies = policy_document["policies"]
    assert register["assessed_on"] == policy_document["assessed_on"]
    for collection, key in (
        ("sources", "id"),
        ("supplementary_sources", "id"),
        ("camera_hosts", "host"),
    ):
        values = [row[key] for row in register[collection]]
        assert len(values) == len(set(values)), f"Duplicate {collection} identity"
        for row in register[collection]:
            assert row["policy"] in policies, f"Missing policy: {row['policy']}"
    assert not (
        {r["id"] for r in register["sources"]}
        & {r["id"] for r in register["supplementary_sources"]}
    )
    for row in register["sources"]:
        assert row["code_checked_on"] <= register["assessed_on"], "Future code check"
        assert row["policy"] not in row["additional_policies"], "Repeated primary policy"
        assert all(key in policies for key in row["additional_policies"]), (
            "Missing additional provider policy"
        )
        if row["current_default"] == "off_until_configured":
            assert row["gating_flags"], "Disabled source needs an identified prerequisite"
    for row in register["camera_hosts"]:
        if row["provider_policy"]:
            assert row["provider_policy"] in policies, "Missing camera provider policy"
    for policy in policies.values():
        validate_policy_dates(policy, policy_document["assessed_on"])
        if "permission_required" in {policy["commercial_use"], policy["hosted_multi_user_use"]}:
            assert {"request_permission", "replace", "legal_review"} & set(policy["actions"])


def validate_policy_dates(policy: dict[str, Any], assessed_on: str) -> None:
    """A failed lookup must not acquire a verification date or permissive rights."""
    checked, attempted = policy["terms_checked_on"], policy["lookup_attempted_on"]
    status = policy["review_status"]
    if status in {"terms_checked", "partial_review"}:
        assert policy["terms_url"] and checked and attempted, "Verified terms need evidence/date"
        assert checked <= attempted <= assessed_on, "Future verification"
    else:
        assert checked is None, "Unchecked terms must not carry a verification date"
        assert policy["commercial_use"] == policy["hosted_multi_user_use"] == "unknown"
        if status in {"lookup_blocked", "lookup_inconclusive"}:
            assert policy["terms_url"] and attempted, "Lookup needs attempted URL/date"
            assert attempted <= assessed_on
        else:
            assert attempted is None, "Unattempted review must not claim a lookup date"

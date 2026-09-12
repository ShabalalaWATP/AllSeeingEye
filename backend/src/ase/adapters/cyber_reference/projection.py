"""Offline import of a bounded, pinned Enterprise ATT&CK STIX release."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from html import unescape
from typing import Any

from ase.adapters.cyber_reference.catalogue import (
    ATTRIBUTION,
    LICENCE_URL,
    LIMITATIONS,
    SOURCE_ID,
    SOURCE_ROOT,
    bounded_text,
    parse_actor_catalogue,
    utc_date,
)
from ase.domain.cyber_actors import MAX_ACTORS, MAX_DESCRIPTION_LENGTH, MAX_NAME_LENGTH

MAX_STIX_BYTES = 80 * 1024 * 1024
MAX_STIX_OBJECTS = 60_000


def _plain_description(value: object) -> str:
    if not isinstance(value, str) or len(value) > 40_000:
        raise ValueError("Invalid actor description")
    # Keep source wording, removing citation syntax and Markdown/HTML presentation.
    text = re.sub(r"\(Citation:[^)]*\)", "", value)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]*>", "", unescape(text))
    text = " ".join(text.replace("*", "").replace("`", "").split())
    text = text.replace("<", "").replace(">", "")
    if len(text) > MAX_DESCRIPTION_LENGTH:
        text = text[: MAX_DESCRIPTION_LENGTH - 1].rsplit(" ", 1)[0] + "…"
    return bounded_text(text, MAX_DESCRIPTION_LENGTH, empty=True)


def _external_id(row: dict[str, Any], prefix: str) -> str:
    references = row.get("external_references", [])
    if not isinstance(references, list) or len(references) > 300:
        raise ValueError("Invalid STIX external references")
    pattern = r"G\d{4}" if prefix == "G" else r"T\d{4}(?:\.\d{3})?"
    for reference in references:
        if not isinstance(reference, dict) or reference.get("source_name") != "mitre-attack":
            continue
        external_id = reference.get("external_id")
        if isinstance(external_id, str) and re.fullmatch(pattern, external_id):
            return external_id
    raise ValueError("STIX object is missing its MITRE external identifier")


def _current(row: dict[str, Any]) -> bool:
    return row.get("revoked", False) is False and row.get("x_mitre_deprecated", False) is False


def _objects(payload: bytes) -> list[dict[str, Any]]:
    if len(payload) > MAX_STIX_BYTES:
        raise ValueError("STIX bundle exceeds its byte bound")
    data = json.loads(payload)
    if not isinstance(data, dict) or data.get("type") != "bundle":
        raise ValueError("Expected a STIX bundle")
    rows = data.get("objects")
    if not isinstance(rows, list) or len(rows) > MAX_STIX_OBJECTS:
        raise ValueError("STIX object count exceeds its bound")
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("Invalid STIX object")
    return rows


def _actor_rows(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups = [row for row in objects if row.get("type") == "intrusion-set" and _current(row)]
    if len(groups) > MAX_ACTORS:
        raise ValueError("STIX group count exceeds its bound")
    techniques = {
        row["id"]: _external_id(row, "T")
        for row in objects
        if row.get("type") == "attack-pattern" and _current(row)
    }
    uses: dict[str, set[str]] = {}
    for row in objects:
        if (
            row.get("type") == "relationship"
            and row.get("relationship_type") == "uses"
            and _current(row)
            and isinstance(row.get("source_ref"), str)
            and isinstance(row.get("target_ref"), str)
            and row["target_ref"] in techniques
        ):
            uses.setdefault(row["source_ref"], set()).add(techniques[row["target_ref"]])
    actors = []
    for row in groups:
        group_id = _external_id(row, "G")
        name = bounded_text(row.get("name"), MAX_NAME_LENGTH)
        aliases = row.get("aliases", [])
        if not isinstance(aliases, list) or len(aliases) > 25:
            raise ValueError("Invalid STIX group aliases")
        associated = sorted(
            {bounded_text(alias, MAX_NAME_LENGTH) for alias in aliases if alias != name},
            key=str.casefold,
        )
        actors.append(
            {
                "group_id": group_id,
                "name": name,
                "associated_names": associated,
                "description": _plain_description(row.get("description", "")),
                "url": f"https://attack.mitre.org/groups/{group_id}/",
                "modified_at": utc_date(row.get("modified")).isoformat(),
                "technique_ids": sorted(uses.get(row["id"], set())),
            }
        )
    return sorted(actors, key=lambda actor: (actor["name"].casefold(), actor["group_id"]))


def project_actor_catalogue(payload: bytes, *, commit: str, retrieved_at: datetime) -> bytes:
    """Project official STIX bytes; never follow links contained in imported data.

    The operator supplies the source commit and retrieval time. SHA-256 preserves
    exact source bytes for reproducibility; it is not proof of publisher identity.
    """
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("A full upstream Git commit is required")
    objects = _objects(payload)
    collections = [row for row in objects if row.get("type") == "x-mitre-collection"]
    if len(collections) != 1 or collections[0].get("name") != "Enterprise ATT&CK":
        raise ValueError("Expected one Enterprise ATT&CK collection")
    collection = collections[0]
    version = bounded_text(collection.get("x_mitre_version"), 12)
    if not re.fullmatch(r"\d{1,3}\.\d{1,3}", version):
        raise ValueError("Invalid ATT&CK release version")
    result = {
        "schema_version": 1,
        "source_id": SOURCE_ID,
        "version": version,
        "released_at": utc_date(collection.get("modified")).isoformat(),
        "retrieved_at": retrieved_at.isoformat(),
        "source_url": (f"{SOURCE_ROOT}{commit}/enterprise-attack/enterprise-attack-{version}.json"),
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "licence_url": LICENCE_URL,
        "attribution": ATTRIBUTION,
        "limitations": LIMITATIONS,
        "actors": _actor_rows(objects),
    }
    projected = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    parse_actor_catalogue(projected)
    return projected

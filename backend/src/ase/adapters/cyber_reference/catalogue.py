"""Validate the bounded generated projection before exposing reference records."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from functools import lru_cache
from importlib.resources import files
from typing import Any

from ase.domain.cyber_actors import (
    MAX_ACTORS,
    MAX_ASSOCIATED_NAMES,
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    MAX_TECHNIQUES,
    CyberActorCatalogue,
    CyberActorReference,
)

SOURCE_ID = "mitre_attack"
LICENCE_URL = "https://attack.mitre.org/resources/terms-of-use/"
SOURCE_ROOT = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/"
MAX_CATALOGUE_BYTES = 2 * 1024 * 1024
ATTRIBUTION = (
    "This product uses MITRE ATT&CK®. © 2026 The MITRE Corporation. "
    "This work is reproduced and distributed with the permission of The MITRE Corporation."
)
LIMITATIONS = (
    "Historical MITRE ATT&CK Enterprise group references, not a list of actors currently active. "
    "Associated names describe reported overlaps and do not establish identical membership "
    "or exact identity equivalence. Descriptions are shortened source text; consult the linked "
    "MITRE record for citations and context. Technique counts cover non-revoked, non-deprecated "
    "techniques and sub-techniques directly linked by this release. Name matches identify text "
    "mentions only, including denials; they do not confirm attribution. Short and shared names "
    "may be omitted from matching. The catalogue is incomplete and does not update automatically."
)


def bounded_text(value: object, maximum: int, *, empty: bool = False) -> str:
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or (not value.strip() and not empty)
        or any(ord(char) < 32 or char in "<>" for char in value)
    ):
        raise ValueError("Invalid bounded reference text")
    return value


def utc_date(value: object) -> datetime:
    text = bounded_text(value, 40)
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Reference dates must include a timezone")
    return parsed.astimezone(UTC)


def _record(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Expected a reference object")
    return value


def _list(value: object, maximum: int) -> list[Any]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError("Reference list exceeds its bound")
    return value


def _actor(value: object) -> CyberActorReference:
    row = _record(value)
    group_id = bounded_text(row.get("group_id"), 5)
    if not re.fullmatch(r"G\d{4}", group_id):
        raise ValueError("Invalid ATT&CK group identifier")
    url = f"https://attack.mitre.org/groups/{group_id}/"
    if row.get("url") != url:
        raise ValueError("Reference links must use canonical MITRE group URLs")
    names = tuple(
        bounded_text(name, MAX_NAME_LENGTH)
        for name in _list(row.get("associated_names"), MAX_ASSOCIATED_NAMES)
    )
    technique_ids = tuple(
        bounded_text(technique, 9) for technique in _list(row.get("technique_ids"), MAX_TECHNIQUES)
    )
    if any(not re.fullmatch(r"T\d{4}(?:\.\d{3})?", item) for item in technique_ids):
        raise ValueError("Invalid ATT&CK technique identifier")
    if len(set(technique_ids)) != len(technique_ids) or len(set(names)) != len(names):
        raise ValueError("Duplicate reference names or techniques")
    return CyberActorReference(
        group_id=group_id,
        name=bounded_text(row.get("name"), MAX_NAME_LENGTH),
        associated_names=names,
        description=bounded_text(row.get("description"), MAX_DESCRIPTION_LENGTH, empty=True),
        url=url,
        modified_at=utc_date(row.get("modified_at")),
        technique_ids=technique_ids,
    )


def parse_actor_catalogue(payload: bytes) -> CyberActorCatalogue:
    """Fail closed on malformed, oversized or externally linked packaged metadata."""
    if len(payload) > MAX_CATALOGUE_BYTES:
        raise ValueError("Reference catalogue exceeds its byte bound")
    data = _record(json.loads(payload))
    if data.get("schema_version") != 1 or data.get("source_id") != SOURCE_ID:
        raise ValueError("Unsupported reference catalogue")
    version = bounded_text(data.get("version"), 12)
    if not re.fullmatch(r"\d{1,3}\.\d{1,3}", version):
        raise ValueError("Invalid ATT&CK release version")
    source_url = bounded_text(data.get("source_url"), 250)
    expected_source = (
        re.escape(SOURCE_ROOT)
        + r"[a-f0-9]{40}/enterprise-attack/enterprise-attack-"
        + re.escape(version)
        + r"\.json"
    )
    if not re.fullmatch(expected_source, source_url) or data.get("licence_url") != LICENCE_URL:
        raise ValueError("Invalid MITRE source or licence URL")
    digest = bounded_text(data.get("source_sha256"), 64)
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Invalid reference source checksum")
    actors = tuple(_actor(row) for row in _list(data.get("actors"), MAX_ACTORS))
    if not actors or len({actor.group_id for actor in actors}) != len(actors):
        raise ValueError("Reference catalogue is empty or has duplicate groups")
    released_at = utc_date(data.get("released_at"))
    retrieved_at = utc_date(data.get("retrieved_at"))
    if retrieved_at < released_at or any(actor.modified_at > released_at for actor in actors):
        raise ValueError("Reference dates are inconsistent")
    return CyberActorCatalogue(
        source_id=SOURCE_ID,
        version=version,
        released_at=released_at,
        retrieved_at=retrieved_at,
        source_url=source_url,
        source_sha256=digest,
        licence_url=LICENCE_URL,
        attribution=bounded_text(data.get("attribution"), 500),
        limitations=bounded_text(data.get("limitations"), 1_000),
        actors=actors,
    )


@lru_cache(maxsize=1)
def load_actor_catalogue() -> CyberActorCatalogue:
    resource = files(__package__).joinpath("enterprise_actors.json")
    with resource.open("rb") as handle:
        payload = handle.read(MAX_CATALOGUE_BYTES + 1)
    return parse_actor_catalogue(payload)

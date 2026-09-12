"""Offline STIX projection excludes withdrawn objects and unsafe presentation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from ase.adapters.cyber_reference.catalogue import parse_actor_catalogue
from ase.adapters.cyber_reference.projection import (
    MAX_STIX_OBJECTS,
    project_actor_catalogue,
)

COMMIT = "a" * 40
RETRIEVED_AT = datetime(2026, 9, 12, tzinfo=UTC)


def _group(group_id: str = "G0001", **extra: object) -> dict[str, Any]:
    return {
        "type": "intrusion-set",
        "id": "intrusion-set--" + group_id,
        "name": "Example Group",
        "modified": "2026-08-01T00:00:00Z",
        "description": (
            "[Example Group](https://example.com/) is a historical group. "
            "(Citation: Example report) <b>Reported activity</b> &amp; context."
        ),
        "aliases": ["Example Group", "Associated Name"],
        "external_references": [
            {
                "source_name": "mitre-attack",
                "external_id": group_id,
                "url": "https://untrusted.example/groups/",
            }
        ],
        **extra,
    }


def _technique(technique_id: str, **extra: object) -> dict[str, Any]:
    return {
        "type": "attack-pattern",
        "id": "attack-pattern--" + technique_id,
        "external_references": [{"source_name": "mitre-attack", "external_id": technique_id}],
        **extra,
    }


def _uses(technique_id: str, **extra: object) -> dict[str, Any]:
    return {
        "type": "relationship",
        "relationship_type": "uses",
        "source_ref": "intrusion-set--G0001",
        "target_ref": "attack-pattern--" + technique_id,
        **extra,
    }


@pytest.fixture
def stix() -> dict[str, Any]:
    return {
        "type": "bundle",
        "objects": [
            {
                "type": "x-mitre-collection",
                "name": "Enterprise ATT&CK",
                "x_mitre_version": "19.2",
                "modified": "2026-08-05T00:00:00Z",
            },
            _group(),
        ],
    }


def _project(stix: object, commit: str = COMMIT) -> bytes:
    return project_actor_catalogue(
        json.dumps(stix).encode(), commit=commit, retrieved_at=RETRIEVED_AT
    )


def test_projects_source_text_without_following_untrusted_links(stix: dict[str, Any]) -> None:
    payload = _project(stix)
    result = parse_actor_catalogue(payload)
    actor = result.actors[0]
    assert actor.description == "Example Group is a historical group. Reported activity & context."
    assert actor.associated_names == ("Associated Name",)
    assert actor.url == "https://attack.mitre.org/groups/G0001/"
    assert result.source_url.endswith(f"/{COMMIT}/enterprise-attack/enterprise-attack-19.2.json")
    assert _project(stix) == payload


def test_only_direct_current_technique_relationships_count(stix: dict[str, Any]) -> None:
    stix["objects"].extend(
        [
            _group("G0002", revoked=True),
            _group("G0003", x_mitre_deprecated=True),
            _technique("T0001"),
            _technique("T0001.001"),
            _technique("T0002", revoked=True),
            _technique("T0003", x_mitre_deprecated=True),
            _technique("T0004"),
            _technique("T0005"),
            _uses("T0001"),
            _uses("T0001"),
            _uses("T0001.001"),
            _uses("T0002"),
            _uses("T0003"),
            _uses("T0004", revoked=True),
            _uses("T0005", x_mitre_deprecated=True),
            _uses("T0004", relationship_type="attributed-to"),
            _uses("T0005", source_ref="malware--example"),
        ]
    )
    result = parse_actor_catalogue(_project(stix))
    assert len(result.actors) == 1
    assert result.actors[0].technique_ids == ("T0001", "T0001.001")


def test_descriptions_are_truncated_on_word_boundary(stix: dict[str, Any]) -> None:
    stix["objects"][1]["description"] = "A historical description. " * 100
    description = parse_actor_catalogue(_project(stix)).actors[0].description
    assert description.endswith("…")
    assert len(description) <= 800


@pytest.mark.parametrize(
    "data",
    [
        [],
        {},
        {"type": "object"},
        {"type": "bundle", "objects": 3},
        {"type": "bundle", "objects": [None]},
        {"type": "bundle", "objects": [{}] * (MAX_STIX_OBJECTS + 1)},
    ],
)
def test_invalid_stix_structure_is_rejected(data: object) -> None:
    with pytest.raises(ValueError):
        _project(data)


@pytest.mark.parametrize("commit", ["master", "../main", "a" * 39, "A" * 40])
def test_full_source_commit_is_required(stix: dict[str, Any], commit: str) -> None:
    with pytest.raises(ValueError, match="commit"):
        _project(stix, commit)


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", "Mobile ATT&CK"), ("x_mitre_version", "19.2/../"), ("modified", "invalid")],
)
def test_wrong_collection_or_metadata_is_rejected(
    stix: dict[str, Any], field: str, value: object
) -> None:
    stix["objects"][0][field] = value
    with pytest.raises(ValueError):
        _project(stix)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", 5),
        pytest.param("description", "x" * 40_001, id="oversized-description"),
        ("external_references", []),
        ("external_references", {}),
        ("external_references", [None, {"source_name": "other"}]),
        ("external_references", [{"source_name": "mitre-attack", "external_id": "bad"}]),
        ("external_references", [{}] * 301),
        ("aliases", "alias"),
        ("aliases", ["name"] * 26),
        ("name", "<script>test</script>"),
    ],
)
def test_invalid_actor_fields_fail_closed(stix: dict[str, Any], field: str, value: object) -> None:
    stix["objects"][1][field] = value
    with pytest.raises(ValueError):
        _project(stix)


def test_excessive_actor_count_fails_without_truncation(stix: dict[str, Any]) -> None:
    stix["objects"].extend(_group(f"G{index:04d}") for index in range(2, 302))
    with pytest.raises(ValueError, match="group count"):
        _project(stix)

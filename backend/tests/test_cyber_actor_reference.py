"""Packaged references stay bounded, historical, attributable and safe to display."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from importlib.resources import files
from typing import Any

import pytest

from ase.adapters.cyber_reference import MITRE_ATTACK_SPEC, load_actor_catalogue
from ase.adapters.cyber_reference.catalogue import (
    MAX_CATALOGUE_BYTES,
    bounded_text,
    parse_actor_catalogue,
)
from ase.domain.cyber_actors import (
    MAX_ACTORS,
    MAX_ASSOCIATED_NAMES,
    MAX_DESCRIPTION_LENGTH,
    MAX_MENTION_TEXT,
    MAX_TECHNIQUES,
    CyberActorReference,
    match_actor_mentions,
)


@pytest.fixture
def catalogue_data() -> dict[str, Any]:
    resource = files("ase.adapters.cyber_reference").joinpath("enterprise_actors.json")
    data: dict[str, Any] = json.loads(resource.read_bytes())
    data["actors"] = data["actors"][:1]
    return data


def _parse(data: object) -> None:
    parse_actor_catalogue(json.dumps(data).encode())


def _actor(name: str, associated: tuple[str, ...] = (), group_id: str = "G0001"):
    return CyberActorReference(
        group_id=group_id,
        name=name,
        associated_names=associated,
        description="Historical reference",
        url=f"https://attack.mitre.org/groups/{group_id}/",
        modified_at=datetime(2026, 1, 1, tzinfo=UTC),
        technique_ids=("T1059",),
    )


def test_packaged_catalogue_provenance_and_known_references() -> None:
    catalogue = load_actor_catalogue()
    assert load_actor_catalogue() is catalogue
    assert catalogue.source_id == MITRE_ATTACK_SPEC.id == "mitre_attack"
    assert catalogue.version == "19.2"
    assert catalogue.released_at.isoformat() == "2026-08-05T21:33:58.496000+00:00"
    assert catalogue.source_sha256 == (
        "dc1639caa5501d720e280cf1cbd8fbe009884a0c9b3e6e9ed9d0c25166c3d8f4"
    )
    assert len(catalogue.actors) == 176
    apt28 = next(actor for actor in catalogue.actors if actor.group_id == "G0007")
    assert apt28.name == "APT28"
    assert "Fancy Bear" in apt28.associated_names
    assert apt28.technique_count == len(apt28.technique_ids) > 0
    assert "currently active" in catalogue.limitations
    assert "exact identity equivalence" in catalogue.limitations
    assert "permission of The MITRE Corporation" in catalogue.attribution
    licence = files("ase.adapters.cyber_reference").joinpath("LICENSE.txt").read_text("utf8")
    assert "© 2026 The MITRE Corporation" in licence
    assert "royalty-free license" in licence


def test_all_packaged_actor_text_and_references_respect_bounds() -> None:
    catalogue = load_actor_catalogue()
    assert len(catalogue.actors) <= MAX_ACTORS
    for actor in catalogue.actors:
        assert len(actor.description) <= MAX_DESCRIPTION_LENGTH
        assert len(actor.associated_names) <= MAX_ASSOCIATED_NAMES
        assert len(actor.technique_ids) <= MAX_TECHNIQUES
        assert "<" not in actor.description
        assert "(Citation:" not in actor.description
        assert actor.url == f"https://attack.mitre.org/groups/{actor.group_id}/"


@pytest.mark.parametrize("payload", [b"[]", b"null", b"{}", b"not json"])
def test_catalogue_rejects_bad_json_or_top_level(payload: bytes) -> None:
    with pytest.raises(ValueError):
        parse_actor_catalogue(payload)


def test_catalogue_rejects_excessive_bytes() -> None:
    with pytest.raises(ValueError, match="byte bound"):
        parse_actor_catalogue(b" " * (MAX_CATALOGUE_BYTES + 1))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("source_id", "other"),
        ("version", "../../x"),
        ("source_url", "https://example.com/source.json"),
        ("licence_url", "javascript:alert(1)"),
        ("source_sha256", "x" * 64),
        ("attribution", "<script>test</script>"),
        ("limitations", None),
        ("released_at", "2026-08-01"),
        ("retrieved_at", "2020-01-01T00:00:00Z"),
        ("actors", []),
        ("actors", "groups"),
    ],
)
def test_catalogue_rejects_invalid_metadata(
    catalogue_data: dict[str, Any], field: str, value: object
) -> None:
    catalogue_data[field] = value
    with pytest.raises(ValueError):
        _parse(catalogue_data)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("group_id", "G00000"),
        ("group_id", "Z0001"),
        ("name", "\x00bad"),
        ("name", " "),
        ("name", 42),
        ("description", "x" * (MAX_DESCRIPTION_LENGTH + 1)),
        ("url", "https://example.com/groups/G0001/"),
        ("associated_names", ["same", "same"]),
        ("associated_names", ["name"] * (MAX_ASSOCIATED_NAMES + 1)),
        ("technique_ids", ["T0001", "T0001"]),
        ("technique_ids", ["G0001"]),
        ("technique_ids", ["T0001"] * (MAX_TECHNIQUES + 1)),
        ("modified_at", "2099-01-01T00:00:00Z"),
    ],
)
def test_catalogue_rejects_invalid_actor_data(
    catalogue_data: dict[str, Any], field: str, value: object
) -> None:
    catalogue_data["actors"][0][field] = value
    with pytest.raises(ValueError):
        _parse(catalogue_data)


def test_catalogue_rejects_duplicate_groups_and_oversized_or_malformed_lists(
    catalogue_data: dict[str, Any],
) -> None:
    actor = catalogue_data["actors"][0]
    for actors in ([actor, actor], [actor] * (MAX_ACTORS + 1), ["bad"]):
        catalogue_data["actors"] = actors
        with pytest.raises(ValueError):
            _parse(catalogue_data)


def test_bounded_text_allows_empty_description_only() -> None:
    assert bounded_text("", 800, empty=True) == ""
    with pytest.raises(ValueError):
        bounded_text("", 120)


def test_mentions_use_exact_boundaries_case_insensitivity_and_one_match_per_group() -> None:
    actor = _actor("APT28", ("Fancy Bear", "Sofacy"))
    assert not match_actor_mentions("APT280 xAPT28 FooFancy Bearbar Sofacy", (actor,))
    matches = match_actor_mentions("FANCY BEAR was mentioned; apt28 was denied.", (actor,))
    assert len(matches) == 1
    assert matches[0].group_id == actor.group_id
    assert matches[0].matched_name == "APT28"


def test_mentions_skip_short_shared_and_excessively_long_associated_names() -> None:
    first = _actor("First Group", ("Shared Actor", "Silence", "x" * 121))
    second = _actor("Second Group", ("Shared Actor",), "G0002")
    assert not match_actor_mentions("Shared Actor and Silence " + "x" * 121, (first, second))
    assert match_actor_mentions("First Group", (first, second))[0].group_id == "G0001"


def test_mentions_escape_regex_and_bound_text_and_catalogue() -> None:
    actor = _actor("Example (Group)")
    assert not match_actor_mentions("Example Group", (actor,))
    assert match_actor_mentions("Example (Group)", (actor,))
    assert not match_actor_mentions(" " * MAX_MENTION_TEXT + "Example (Group)", (actor,))
    actors = tuple(replace(actor, name=f"Group{i:04d}", group_id=f"G{i:04d}") for i in range(301))
    assert not match_actor_mentions("Group0300", actors)

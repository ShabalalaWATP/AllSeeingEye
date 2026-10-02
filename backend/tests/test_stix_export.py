"""Offline official-schema conformance, determinism and no inferred observables."""

import json
from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from ase.adapters.reports import stix
from ase.adapters.reports.stix import FrozenStixRenderer
from ase.domain.errors import InvalidRequest
from ase.domain.stix import StixTlp
from report_documents_helpers import document_records


def cyber_records(owner=None):
    record, version = document_records(owner)
    item = replace(
        version.evidence[0],
        category="cyber",
        title="CVE-2021-44228 advisory",
        summary="An advisory, not an indicator.",
        url="https://attack.mitre.org/groups/G0001/",
    )
    return record, replace(version, evidence=(item,))


@pytest.mark.parametrize("tlp", list(StixTlp))
def test_stix_is_deterministic_and_valid_against_vendored_oasis_schemas(tlp):
    record, version = cyber_records()
    writer = FrozenStixRenderer()
    content = writer.render(record, version, tlp)
    assert writer.render(record, version, tlp) == content
    bundle = json.loads(content)
    assert bundle["type"] == "bundle" and UUID(bundle["id"].split("--")[1]).version == 5
    root = Path(__file__).parent / "fixtures/stix21/schemas"
    schemas = [json.loads(path.read_text(encoding="utf-8")) for path in root.rglob("*.json")]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    by_title = {schema["title"]: schema for schema in schemas if "title" in schema}
    for obj in bundle["objects"]:
        Draft202012Validator(by_title[obj["type"]], registry=registry).validate(obj)
        assert "confidence" not in obj and obj["type"] != "indicator"
    assert {obj["type"] for obj in bundle["objects"]} == {
        "marking-definition",
        "report",
        "note",
        "vulnerability",
        "intrusion-set",
    }
    assert [obj["name"] for obj in bundle["objects"] if obj["type"] == "vulnerability"] == [
        "CVE-2021-44228"
    ]
    assert writer.render(record, version, StixTlp.RED) != writer.render(
        record, version, StixTlp.GREEN
    )


def test_no_actor_inferred_from_a_name_or_unsafe_link_and_no_cve_invented():
    record, version = cyber_records()
    item = replace(
        version.evidence[0],
        title="APT example",
        summary="An unknown actor",
        url="https://user:password@example.test",
    )
    bundle = json.loads(
        FrozenStixRenderer().render(record, replace(version, evidence=(item,)), StixTlp.AMBER)
    )
    assert {obj["type"] for obj in bundle["objects"]} == {"marking-definition", "report", "note"}
    assert "password" not in json.dumps(bundle)
    with pytest.raises(InvalidRequest):
        FrozenStixRenderer().render(record, replace(version, evidence=()), StixTlp.AMBER)


def test_stix_rejects_oversized_input_before_materialising_objects(monkeypatch):
    record, version = cyber_records()
    monkeypatch.setattr(stix, "MAX_PACKAGE_BYTES", 10)
    with pytest.raises(InvalidRequest, match="8 MiB"):
        FrozenStixRenderer().render(record, version, StixTlp.AMBER)


def test_stix_caps_object_count_without_truncating_silently(monkeypatch):
    record, version = cyber_records()
    monkeypatch.setattr(stix, "MAX_STIX_OBJECTS", 1)
    with pytest.raises(InvalidRequest, match="3,000"):
        FrozenStixRenderer().render(record, version, StixTlp.AMBER)

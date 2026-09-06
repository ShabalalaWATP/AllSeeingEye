"""Frozen research attribution and identity hints stay bounded, typed and inert."""

import json
from dataclasses import FrozenInstanceError

import pytest

from ase.api.schemas_report_evidence import ReportEvidenceOut
from ase.domain.events import MAX_ATTRIBUTE_CHARS, MAX_ATTRIBUTES, freeze_attributes
from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_attributes import (
    MAX_EXACT_INTEGER,
    EvidenceAttribute,
    evidence_attributes_from_list,
    evidence_attributes_to_list,
    freeze_evidence_attributes,
)
from ase.domain.report_records import evidence_from_list, evidence_to_list
from feeds_helpers import NOW, make_event


def test_frozen_report_retains_attribution_import_rows_identifiers_and_time_hints():
    attributes = {
        "original_publisher": "Named publisher",
        "original_account": "account@example.social",
        "original_publisher_url": "https://publisher.example/source",
        "collection_feed": "Search feed",
        "page": 2,
        "row": 17,
        "cik": "0000123456",
        "dns_record_type": "TXT",
        "registry_checked_at": NOW.isoformat(),
        "approximate": True,
        "weight": 1.25,
        "missing_attribution": None,
        "supplied_text": "<script>alert('inert text')</script>",
    }
    event = make_event().with_changes(attributes=freeze_attributes(attributes))
    frozen = EvidenceItem.from_event("E1", event, NOW, source_name="Feed", independence_key="")
    attributes["original_publisher"] = "Changed after capture"
    encoded = json.loads(json.dumps(evidence_to_list((frozen,))))
    restored = evidence_from_list(encoded)[0]
    assert restored == frozen
    values = {entry.key: entry.value for entry in restored.attributes}
    assert values["original_publisher"] == "Named publisher"
    assert values["page"] == 2 and values["row"] == 17
    assert values["cik"] == "0000123456" and values["registry_checked_at"] == NOW.isoformat()
    assert values["dns_record_type"] == "TXT" and values["approximate"] is True
    output = ReportEvidenceOut.model_validate(restored).model_dump(mode="json")
    assert {row["key"]: row["value"] for row in output["attributes"]} == values
    assert output["attributes"][-1]["value"] == "<script>alert('inert text')</script>"
    with pytest.raises(FrozenInstanceError):
        restored.attributes[0].value = "Changed"  # type: ignore[misc]


def test_freezing_bounds_scalar_metadata_without_accepting_nested_objects_or_nonfinite_numbers():
    unsafe = {
        "x" * 65: "oversized key",
        "": "empty key",
        "nan": float("nan"),
        "infinity": float("inf"),
        "nested": {"raw": "object"},
        "huge": MAX_EXACT_INTEGER + 1,
        "long": "x" * 1000,
        "valid": False,
    }
    result = freeze_evidence_attributes(unsafe)  # type: ignore[arg-type]
    assert result == (
        EvidenceAttribute("long", "x" * MAX_ATTRIBUTE_CHARS),
        EvidenceAttribute("valid", False),
    )
    bounded = freeze_evidence_attributes({f"field{i}": i for i in range(MAX_ATTRIBUTES + 5)})
    assert len(bounded) == MAX_ATTRIBUTES


def test_legacy_missing_or_null_attributes_remain_empty():
    item = EvidenceItem.from_event(
        "E1", make_event(), NOW, source_name="Source", independence_key=""
    )
    row = evidence_to_list((item,))[0]
    assert row["attributes"] == []
    row.pop("attributes")
    assert evidence_from_list([row])[0].attributes == ()
    assert evidence_attributes_from_list(None) == ()
    row["attributes"] = None
    assert evidence_from_list([row])[0].attributes == ()


@pytest.mark.parametrize(
    "data",
    [
        {},
        "metadata",
        [{"key": "k"}],
        [{"key": "k", "value": "v", "extra": True}],
        [{"key": "", "value": "v"}],
        [{"key": "x" * 65, "value": "v"}],
        [{"key": "k", "value": []}],
        [{"key": "k", "value": "x" * 501}],
        [{"key": "k", "value": float("nan")}],
        [{"key": "k", "value": MAX_EXACT_INTEGER + 1}],
        [{"key": "k", "value": 1}, {"key": "k", "value": 2}],
        [{"key": f"k{i}", "value": i} for i in range(MAX_ATTRIBUTES + 1)],
    ],
)
def test_malformed_saved_metadata_cannot_be_silently_coerced(data):
    with pytest.raises(ValueError):
        evidence_attributes_from_list(data)


def test_encoding_preserves_json_scalar_types_and_rejects_invalid_constructed_rows():
    rows = tuple(
        EvidenceAttribute(f"k{i}", value) for i, value in enumerate(("01", 1, 1.5, True, None))
    )
    encoded = evidence_attributes_to_list(rows)
    assert evidence_attributes_from_list(json.loads(json.dumps(encoded))) == rows
    with pytest.raises(ValueError):
        evidence_attributes_to_list([EvidenceAttribute("k", float("inf"))])

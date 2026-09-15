"""The frozen V01 manifest is local, bounded, source-versioned and honestly labelled."""

import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from evaluations.v01.corpus import DEFAULT_ROOT, MAX_CASE_BYTES, _read_bounded, load_corpus
from evaluations.v01.schema import ContractCase, Manifest
from pydantic import ValidationError

CORPUS = load_corpus()


@pytest.fixture
def copied_corpus(tmp_path: Path) -> Path:
    target = tmp_path / "corpus"
    target.mkdir()
    shutil.copyfile(DEFAULT_ROOT / "manifest.json", target / "manifest.json")
    shutil.copytree(DEFAULT_ROOT / "cases", target / "cases")
    return target


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_sixty_packets_have_an_explicit_split_and_reviewable_references() -> None:
    assert Counter(case.domain for case in CORPUS.cases) == Counter(
        entry.domain for entry in CORPUS.manifest.cases
    )
    assert set(Counter(case.domain for case in CORPUS.cases).values()) == {10}
    assert Counter(case.split for case in CORPUS.cases) == {"development": 48, "held_out": 12}
    assert all(case.evidence_origin == "synthetic_assistant_authored" for case in CORPUS.cases)
    assert all(case.human_review_status == "pending" for case in CORPUS.cases)
    assert all(
        case.requirements and case.known_pitfalls and case.acceptable_abstentions
        for case in CORPUS.cases
    )
    assert "not blind" in CORPUS.manifest.held_out_limitations
    serial = [case for case in CORPUS.cases if case.split == "held_out"]
    assert len(serial) == 12 and all(case.edition is not None for case in serial)
    assert len({case.edition.subscription_id for case in serial if case.edition}) == 6


@pytest.mark.parametrize(
    "field,value",
    [
        ("evidence_origin", "captured_public"),
        ("label_origin", "independent_human_labels"),
        ("human_review_status", "approved"),
        ("unrecognised", "ignored"),
    ],
)
def test_no_silent_promotion_to_captured_or_human_reviewed_evidence(field: str, value: str) -> None:
    data = CORPUS.cases[0].model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        ContractCase.model_validate(data)


@pytest.mark.parametrize(
    "change",
    [
        "text",
        "url",
        "partial_date",
        "naive_date",
        "duplicate_packet",
        "duplicate_requirement",
        "reference",
        "quote",
        "version",
        "window",
    ],
)
def test_packet_and_reference_corruption_is_rejected(change: str) -> None:
    data = CORPUS.cases[0].model_dump(mode="json")
    if change == "text":
        data["packet"][0]["summary"] += " changed"
    elif change == "url":
        data["packet"][0]["url"] = "https://127.0.0.1/private"
    elif change == "partial_date":
        data["packet"][0]["publication_precision"] = "month"
    elif change == "naive_date":
        data["packet"][0]["published_at"] = "2026-09-12T00:00:00"
    elif change == "duplicate_packet":
        data["packet"].append(data["packet"][0])
    elif change == "duplicate_requirement":
        data["requirements"].append(data["requirements"][0])
    elif change == "reference":
        data["requirements"][0]["useful_packet_ids"] = ["unknown"]
    elif change == "quote":
        data["requirements"][0]["expected_passages"][0]["text"] = "absent quotation"
    elif change == "version":
        data["requirements"][0]["expected_passages"][0]["packet_sha256"] = "a" * 64
    else:
        data["scope"]["until"] = data["scope"]["since"]
    with pytest.raises(ValidationError):
        ContractCase.model_validate(data)


@pytest.mark.parametrize(
    "change", ["nonconsecutive", "timestamp", "success", "duplicate_claim", "duplicate_evidence"]
)
def test_edition_input_must_be_unambiguous_and_consecutive(change: str) -> None:
    data = next(case for case in CORPUS.cases if case.id == "cyber_09").model_dump(mode="json")
    edition = data["edition"]
    if change == "nonconsecutive":
        edition["current"]["number"] = 4
    elif change == "timestamp":
        edition["current"]["produced_at"] = edition["previous"]["produced_at"]
    elif change == "success":
        edition["successful_providers"] = ["unattempted"]
    elif change == "duplicate_claim":
        edition["current"]["claims"] *= 2
    else:
        edition["current"]["evidence"] *= 2
    with pytest.raises(ValidationError):
        ContractCase.model_validate(data)


def test_case_needs_an_executable_probe_and_valid_area() -> None:
    data = CORPUS.cases[0].model_dump(mode="json")
    data["probes"] = []
    with pytest.raises(ValidationError, match="executable"):
        ContractCase.model_validate(data)
    for bounds, point in (([0, 20, 10, 10], [1, 1]), ([0, 0, 10, 10], [200, 0])):
        data["probes"] = [
            {"kind": "point_in_area", "bounds": bounds, "point": point, "expected_inside": False}
        ]
        with pytest.raises(ValidationError, match="Invalid evaluation"):
            ContractCase.model_validate(data)


def test_frozen_file_hash_prevents_unnoticed_case_edits(copied_corpus: Path) -> None:
    path = copied_corpus / CORPUS.manifest.cases[0].path
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="digest mismatch"):
        load_corpus(copied_corpus)


@pytest.mark.parametrize("change", ["path", "duplicate", "domain", "split", "identity"])
def test_manifest_rejects_paths_duplicates_or_wrong_distribution(
    copied_corpus: Path, change: str
) -> None:
    path = copied_corpus / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if change == "path":
        data["cases"][0]["path"] = "../external.json"
    elif change == "duplicate":
        data["cases"][1] = data["cases"][0]
    elif change == "domain":
        data["cases"][0]["domain"] = "cyber"
    elif change == "split":
        data["cases"][0]["split"] = "held_out"
    else:
        data["cases"][0]["id"] = "different_identity"
    _write_json(path, data)
    with pytest.raises(ValueError):
        load_corpus(copied_corpus)


def test_shared_editions_cannot_change_between_cases_even_with_rehashed_file(
    copied_corpus: Path,
) -> None:
    manifest_path = copied_corpus / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = next(item for item in manifest["cases"] if item["id"] == "cyber_10")
    path = copied_corpus / entry["path"]
    case = json.loads(path.read_text(encoding="utf-8"))
    case["edition"]["previous"]["claims"][0]["likelihood"] = "unlikely"
    _write_json(path, case)
    entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="shared frozen edition"):
        load_corpus(copied_corpus)


def test_loader_bounds_and_path_confinement(tmp_path: Path) -> None:
    oversized = tmp_path / "large.json"
    oversized.write_bytes(b"x" * (MAX_CASE_BYTES + 1))
    with pytest.raises(ValueError, match="size bound"):
        _read_bounded(oversized, tmp_path)
    with pytest.raises(ValueError, match="escapes"):
        _read_bounded(tmp_path / ".." / "outside.json", tmp_path)
    data = CORPUS.manifest.model_dump(mode="json")
    data["cases"].pop()
    with pytest.raises(ValidationError):
        Manifest.model_validate(data)

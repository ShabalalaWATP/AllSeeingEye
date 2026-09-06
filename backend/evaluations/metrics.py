"""Deterministic structural checks, deliberately separate from semantic accuracy."""

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from evaluations.casebook import EvaluationCase


def ratio(numerator: int, denominator: int) -> dict[str, int | float | None]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def statements(body: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Review units are report fields, not an automatic extraction of atomic propositions."""
    units: list[dict[str, Any]] = []

    def add(key: str, text: str, supports: list[str], counters: list[str] | None = None) -> None:
        units.append(
            {
                "id": key,
                "text": text,
                "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "supporting_evidence": supports,
                "contradicting_evidence": counters or [],
            }
        )

    for index, item in enumerate(body.get("key_judgements", [])):
        add(
            f"judgement.{index}",
            item["statement"],
            list(item.get("supporting_evidence", [])),
            list(item.get("contradicting_evidence", [])),
        )
    for theme_index, theme in enumerate(body.get("reporting", [])):
        for item_index, item in enumerate(theme.get("items", [])):
            add(
                f"reporting.{theme_index}.{item_index}",
                item["text"],
                list(item.get("evidence", [])),
            )
    for index, item in enumerate(body.get("assessment", [])):
        add(f"assessment.{index}", item["text"], list(item.get("evidence", [])))
    for index, item in enumerate(body.get("alternative_hypotheses", [])):
        add(
            f"alternative.{index}",
            f"{item['text']} {item['why_less_likely']}",
            list(item.get("evidence", [])),
        )
    return units


def citation_references(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"evidence", "supporting_evidence", "contradicting_evidence"}:
                if isinstance(child, (list, tuple)):
                    refs.extend(item for item in child if isinstance(item, str))
            else:
                refs.extend(citation_references(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            refs.extend(citation_references(child))
    return refs


def deterministic_metrics(case: EvaluationCase, report: Mapping[str, Any]) -> dict[str, Any]:
    evidence = report["evidence"]
    labels = {item["label"] for item in evidence}
    selected_ids = {item["event_id"] for item in evidence}
    label_to_id = {item["label"]: item["event_id"] for item in evidence}
    body = report["body"]
    refs = citation_references(body)
    cited_ids = {label_to_id[label] for label in refs if label in label_to_id}
    required = case.event_ids(case.reference.required_event_keys)
    counters = case.event_ids(case.reference.counterevidence_event_keys)
    raw_refs: list[str] = []
    invalid_json = 0
    for call in report["model_calls"]:
        if call["schema_name"] != "report" or "content" not in call:
            continue
        try:
            raw_refs.extend(citation_references(json.loads(call["content"])))
        except (ValueError, RecursionError):
            invalid_json += 1
    claims = statements(body)
    organisation_count = report["quality"]["independent_organisations"]
    expected = case.reference.expected_declared_organisation_groups
    return {
        "metric_kind": "deterministic structural checks, not factual accuracy",
        "raw_citation_reference_validity": ratio(
            sum(ref in labels for ref in raw_refs), len(raw_refs)
        ),
        "final_citation_reference_validity": ratio(sum(ref in labels for ref in refs), len(refs)),
        "raw_report_json_parse_failures": invalid_json,
        "uncited_statement_fields": sum(not claim["supporting_evidence"] for claim in claims),
        "statement_fields": len(claims),
        "required_evidence_selected_recall": ratio(len(required & selected_ids), len(required)),
        "required_evidence_cited_recall": ratio(len(required & cited_ids), len(required)),
        "counterevidence_selected_recall": ratio(len(counters & selected_ids), len(counters)),
        "counterevidence_referenced_any_role_recall": ratio(
            len(counters & cited_ids), len(counters)
        ),
        "declared_organisation_groups": organisation_count,
        "expected_declared_organisation_groups_match": None
        if expected is None
        else organisation_count == expected,
        "validation_errors": sum(finding["severity"] == "error" for finding in report["findings"]),
        "validation_warnings": sum(
            finding["severity"] == "warning" for finding in report["findings"]
        ),
        "human_citation_entailment": None,
        "human_unsupported_statement_rate": None,
        "human_counterevidence_adequacy": None,
    }

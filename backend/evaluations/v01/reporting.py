"""Explicit denominators and limits for the synthetic contract track."""

import platform
from collections import defaultdict
from time import perf_counter
from typing import Any

from evaluations.v01.contracts import CheckResult, check_case, serialise_checks
from evaluations.v01.corpus import Corpus
from evaluations.v01.schema import Split

UNMEASURED = {
    "required_question_coverage": "No generated report is assessed in the contract track.",
    "curated_packet_retrieval_recall": "Packets are supplied directly; no retrieval is run.",
    "passage_support": "Literal presence does not establish semantic support.",
    "date_attribution_number_accuracy": "Literal indicators do not measure factual accuracy.",
    "counterevidence_retention": "No collection, selection or synthesis stage is run.",
    "appropriate_analytical_abstention": "A coverage classification is not a written abstention.",
    "privacy_authorisation_budget_publication_invariants": (
        "Pure probes do not execute these paths."
    ),
    "human_change_precision_recall": "No human-reviewed model edition output is available.",
}
MATERIAL_STATES = frozenset(
    {
        "assessment_changed",
        "significant_contradiction_or_correction",
    }
)


def ratio(numerator: int, denominator: int) -> dict[str, int | float | None]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _metrics(checks: list[CheckResult]) -> dict[str, Any]:
    by_contract: dict[str, list[CheckResult]] = defaultdict(list)
    for check in checks:
        by_contract[check.contract].append(check)
    result: dict[str, Any] = {
        name: ratio(sum(item.passed for item in items), len(items))
        for name, items in sorted(by_contract.items())
    }
    changes = by_contract.get("edition_state", [])
    true_positive = sum(
        item.expected in MATERIAL_STATES and item.actual in MATERIAL_STATES for item in changes
    )
    result["synthetic_projection_change_precision"] = ratio(
        true_positive,
        sum(item.actual in MATERIAL_STATES for item in changes),
    )
    result["synthetic_projection_change_recall"] = ratio(
        true_positive,
        sum(item.expected in MATERIAL_STATES for item in changes),
    )
    gaps = [item for item in changes if item.expected in {"insufficient_coverage", "failure"}]
    result["no_data_gap_classification"] = ratio(sum(item.passed for item in gaps), len(gaps))
    return result


def evaluate(corpus: Corpus, split: Split | None = None) -> dict[str, Any]:
    cases = [case for case in corpus.cases if split is None or case.split == split]
    rows: list[dict[str, Any]] = []
    groups: dict[str, list[CheckResult]] = defaultdict(list)
    all_checks: list[CheckResult] = []
    for case in cases:
        start = perf_counter()
        checks = check_case(case)
        elapsed = (perf_counter() - start) * 1000
        all_checks.extend(checks)
        groups[f"{case.domain}/{case.requested_depth}"].extend(checks)
        rows.append(
            {
                "case_id": case.id,
                "domain": case.domain,
                "split": case.split,
                "requested_depth": case.requested_depth,
                "passed": all(item.passed for item in checks),
                "elapsed_ms": elapsed,
                "checks": serialise_checks(checks),
            }
        )
    return {
        "schema_version": "ase-v01-contract-results-1",
        "track": "offline_synthetic_contracts",
        "manifest_sha256": corpus.manifest_sha256,
        "label_origin": corpus.manifest.label_origin,
        "human_review_status": "pending",
        "case_count": len(rows),
        "passed_case_count": sum(row["passed"] for row in rows),
        "metrics": _metrics(all_checks),
        "by_domain_and_declared_depth": {
            key: _metrics(value) for key, value in sorted(groups.items())
        },
        "unmeasured": {
            name: {**ratio(0, 0), "reason": reason} for name, reason in UNMEASURED.items()
        },
        "execution": {
            "python": platform.python_version(),
            "platform": platform.system(),
            "provider_requests": 0,
            "model_calls": 0,
            "external_cost_usd": 0,
            "external_cost_basis": "known_zero_no_external_calls",
            "elapsed_ms": sum(row["elapsed_ms"] for row in rows),
        },
        "limitations": [
            "All evidence and reference expectations are synthetic and assistant-authored.",
            "Declared depth groups describe scenarios; no depth-specific planning or model is run.",
            "Change metrics test frozen structured projections, not semantic extraction or truth.",
            "Local function timing excludes acquisition, models, persistence and UI latency.",
            corpus.manifest.held_out_limitations,
        ],
        "cases": rows,
    }

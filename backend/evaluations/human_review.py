"""A separate, explicitly attributed semantic review with output-fingerprint matching."""

from typing import Any

from evaluations.metrics import ratio, statements


def review_template(results: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for case in results["cases"]:
        claims = []
        for unit in statements(case["report"]["body"]):
            refs = [(label, "supports") for label in unit["supporting_evidence"]]
            refs.extend((label, "contradicts") for label in unit["contradicting_evidence"])
            claims.append(
                {
                    **unit,
                    "supported": None,
                    "notes": "",
                    "citations": [
                        {"label": label, "role": role, "relationship_correct": None}
                        for label, role in dict.fromkeys(refs)
                    ],
                }
            )
        cases.append(
            {
                "case_id": case["case_id"],
                "case_sha256": case["case_sha256"],
                "statements": claims,
                "counterevidence_adequately_addressed": None,
                "required_caveats_addressed": None,
                "notes": "",
            }
        )
    return {
        "run_id": results["run_id"],
        "label_source": "human",
        "reviewer": "",
        "instructions": "Read each report and its frozen evidence against the synthetic reference "
        "rubric. Fill true/false for assessed fields; leave uncertain or unreviewed fields null. "
        "supported=false means this statement field contains at least one unsupported factual "
        "claim or unjustified inference. A plausible forecast alone is not evidence of support. "
        "Check whether each citation supports or contradicts as declared. Do not edit ids, hashes "
        "or statement text. Record notes for disagreements with the reference rubric.",
        "cases": cases,
    }


def human_metrics(results: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    if review.get("run_id") != results["run_id"] or review.get("label_source") != "human":
        raise ValueError("Review must declare human labels for this exact run.")
    if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        raise ValueError("Provide the human reviewer's name or pseudonym.")
    expected = review_template(results)
    expected_cases = {case["case_id"]: case for case in expected["cases"]}
    seen: set[str] = set()
    supports: list[bool] = []
    citations: list[bool] = []
    counterevidence: list[bool] = []
    caveats: list[bool] = []
    total_statements = sum(len(case["statements"]) for case in expected["cases"])
    total_citations = sum(
        len(unit["citations"]) for case in expected["cases"] for unit in case["statements"]
    )

    def collect(value: Any, destination: list[bool]) -> None:
        if value is not None:
            if not isinstance(value, bool):
                raise ValueError("Semantic labels must be true, false or null.")
            destination.append(value)

    for case in review.get("cases", []):
        case_id = case["case_id"]
        reference = expected_cases.get(case_id)
        if (
            case_id in seen
            or reference is None
            or case.get("case_sha256") != reference["case_sha256"]
        ):
            raise ValueError(
                "Review case ids and fingerprints must match this run without duplicates."
            )
        seen.add(case_id)
        units = {unit["id"]: unit for unit in reference["statements"]}
        seen_units: set[str] = set()
        for unit in case.get("statements", []):
            actual = units.get(unit["id"])
            if (
                actual is None
                or unit["id"] in seen_units
                or any(unit.get(key) != actual[key] for key in ("text", "text_sha256"))
            ):
                raise ValueError(
                    "Statement ids, text and fingerprints must match without duplicates."
                )
            seen_units.add(unit["id"])
            collect(unit.get("supported"), supports)
            declared = {(item["label"], item["role"]) for item in actual["citations"]}
            seen_refs: set[tuple[str, str]] = set()
            for citation in unit.get("citations", []):
                pair = (citation["label"], citation["role"])
                if pair not in declared or pair in seen_refs:
                    raise ValueError(
                        "Citation review must refer to a unique citation in this statement."
                    )
                seen_refs.add(pair)
                collect(citation.get("relationship_correct"), citations)
        collect(case.get("counterevidence_adequately_addressed"), counterevidence)
        collect(case.get("required_caveats_addressed"), caveats)
    return {
        "metric_kind": "self-declared human semantic review, not automatic scoring",
        "reviewer": review["reviewer"],
        "run_id": results["run_id"],
        "statement_review_coverage": ratio(len(supports), total_statements),
        "unsupported_statement_field_rate": ratio(
            sum(not item for item in supports), len(supports)
        ),
        "citation_relationship_correctness": ratio(sum(citations), len(citations)),
        "citation_review_coverage": ratio(len(citations), total_citations),
        "counterevidence_adequacy": ratio(sum(counterevidence), len(counterevidence)),
        "counterevidence_review_coverage": ratio(len(counterevidence), len(expected_cases)),
        "required_caveats_adequacy": ratio(sum(caveats), len(caveats)),
        "required_caveats_review_coverage": ratio(len(caveats), len(expected_cases)),
        "cases_in_review": len(seen),
        "total_cases": len(expected_cases),
    }

"""Check analytical prose added or changed after the draft validator ran."""

from ase.domain.doctrine import has_numeric_likelihood, scan_likelihood
from ase.domain.reports import ReportBody
from ase.domain.validation import Finding, Severity


def check_analytical_prose(body: ReportBody) -> tuple[Finding, ...]:
    """Keep forbidden or numeric chance language out of non-judgement analysis.

    Judgement statements and reporting are checked by validate_body. An ordinary
    cited figure, such as 6% inflation, is not a numeric probability.
    """
    passages = [("sourcing_statement", body.sourcing_statement)]
    for judgement in body.key_judgements:
        passages.extend(
            (f"{judgement.id}.indicator[{index}]", text)
            for index, text in enumerate(judgement.indicators)
        )
    passages.extend((f"assessment[{index}]", row.text) for index, row in enumerate(body.assessment))
    passages.extend(
        (f"assumption[{index}]", row.text) for index, row in enumerate(body.assumptions)
    )
    for index, alternative in enumerate(body.alternative_hypotheses):
        passages.extend(
            (
                (f"alternative[{index}].text", alternative.text),
                (f"alternative[{index}].why_less_likely", alternative.why_less_likely),
            )
        )
    passages.extend(
        (f"warning[{index}]", text)
        for index, text in enumerate(body.indicators_and_warning.changes)
    )
    passages.extend((f"gap[{index}]", row.text) for index, row in enumerate(body.gaps))
    passages.extend(
        (f"recommendation[{index}]", text)
        for index, text in enumerate(body.collection_recommendations)
    )
    findings = []
    for location, text in passages:
        scan = scan_likelihood(text)
        if scan.forbidden or has_numeric_likelihood(text):
            findings.append(
                Finding(
                    "yardstick",
                    Severity.ERROR,
                    location,
                    "Analytical prose uses forbidden or numeric chance language; "
                    "use the qualitative yardstick in a key judgement",
                )
            )
    return tuple(findings)

"""Plain-text citation-check projection shared by Markdown and document exports."""

from ase.domain.citation_checks import CitationStatus, ReportCitationChecks

STATUS_LABELS = {
    CitationStatus.ABSENT: "Excerpt or citation absent",
    CitationStatus.CONTEXT_INSUFFICIENT: "Context insufficient",
    CitationStatus.EXCERPT_PRESENT: "Exact excerpt present, meaning unverified",
    CitationStatus.REVIEW_REQUIRED: "Literal mismatch indicators require review",
}


def citation_sections(
    checks: ReportCitationChecks | None,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if checks is None:
        return (("Literal citation checks", ("No citation checks were saved for this version.",)),)
    sections = [
        (
            "Literal citation checks",
            (
                f"Method: {checks.method_version}.",
                *checks.limitations,
                *(("No key judgements were available to check.",) if not checks.judgements else ()),
            ),
        )
    ]
    for judgement in checks.judgements:
        lines = [f"Result: {STATUS_LABELS[judgement.status]}.", *judgement.reasons]
        for citation in judgement.citations:
            relation = "supporting" if citation.relation == "supporting" else "opposing"
            lines.append(
                f"{citation.label}, model-assigned {relation} citation: "
                f"{STATUS_LABELS[citation.status]}."
            )
            lines.extend(citation.reasons)
            if citation.excerpt is not None:
                excerpt = citation.excerpt
                lines.append(
                    f"Original {excerpt.field}, character offsets "
                    f"{excerpt.start} to {excerpt.end} (end excluded):"
                )
                lines.append(excerpt.text)
                lines.append(f"Excerpt SHA-256: {excerpt.sha256}.")
            for indicator in citation.indicators:
                lines.append(
                    f"Review indicator: {indicator.kind.replace('_', ' ')}. "
                    f"Claim values: {', '.join(indicator.claim_values) or 'none'}; "
                    f"excerpt values: {', '.join(indicator.excerpt_values) or 'none'}. "
                    f"{indicator.explanation}"
                )
        sections.append((f"{judgement.judgement_id}: literal citation checks", tuple(lines)))
    return tuple(sections)

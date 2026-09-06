"""Shared frozen collection receipts, with no inference from empty or unavailable sources."""

from ase.domain.research_records import ResearchReceipt


def research_sections(receipt: ResearchReceipt | None) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if receipt is None:
        return (("Collection coverage", ("No collection receipt was saved for this version.",)),)
    lines = [
        f"Policy: {receipt.policy_version}. Mode: {receipt.mode}; focus: {receipt.focus}.",
        f"Research question: {receipt.question}",
        f"Publication window: {receipt.since.isoformat()} to {receipt.until.isoformat()}.",
        f"Requested languages: {', '.join(receipt.languages) or 'none recorded'}.",
        f"Planned search terms: {', '.join(receipt.terms) or 'none recorded'}.",
        f"Collected items: {receipt.collected_items} (new public collection). "
        "Selection for this report is a separate step.",
        "Publication dates are not necessarily event dates. Empty or unavailable sources do not "
        "establish absence of events. Collection does not verify claims.",
    ]
    if not receipt.terms:
        lines.append(
            "Query planning is missing: no targeted search terms were recorded. "
            "The receipts below identify what was actually attempted."
        )
    if not receipt.attempts:
        lines.append("No sources were attempted.")
    for attempt in receipt.attempts:
        count_kind = (
            "retained items"
            if attempt.source_id == "research-reused-evidence"
            else "additional items"
        )
        lines.append(
            f"{attempt.source_name} ({attempt.source_id}): "
            f"{attempt.status.value.replace('_', ' ')}, {attempt.result_count} {count_kind}; "
            f"language {attempt.language or 'not recorded'}. {attempt.explanation}"
        )
    return (("Collection coverage", tuple(lines)),)

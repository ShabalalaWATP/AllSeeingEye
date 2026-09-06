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
    if receipt.plan is not None:
        plan = receipt.plan
        lines.append(
            f"Frozen source plan ({plan.policy_version}): at most {plan.request_limit} requests, "
            f"{plan.seconds_limit:g} seconds and {plan.item_limit} collected items. "
            "The preview is deterministic; run-time transformations are recorded separately. "
            "The plan does not establish complete historical coverage."
        )
        for task in plan.tasks:
            if task.selected:
                lines.append(
                    f"Selected task {task.source_name} ({task.source_id}): "
                    f"{task.provenance}; language {task.language or 'not specified'}; "
                    f"query language {task.query_language or 'original terms'}; "
                    f"terms: {', '.join(task.terms) or 'none supplied'}. {task.temporal_scope}"
                )
    lines.extend(transformation_lines(receipt))
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


def transformation_lines(receipt: ResearchReceipt) -> list[str]:
    lines: list[str] = []
    if receipt.plan is not None and receipt.plan.translation is not None:
        transformation = receipt.plan.translation
        lines.append(
            f"Query translation: {transformation.status}; "
            f"model {transformation.model or 'not used'}. "
            "Translated meaning is unverified."
        )
        lines.append("Original terms: " + ", ".join(transformation.original_terms))
        for variant in transformation.variants:
            lines.append(f"Translated terms ({variant.language}): {', '.join(variant.terms)}")
    for index, collection_pass in enumerate(receipt.passes, 1):
        lines.append(
            f"Collection pass {index}, sharing the run budget: " + ", ".join(collection_pass.terms)
        )
        for attempt in collection_pass.attempts:
            lines.append(
                f"Pass {index}: {attempt.source_name} ({attempt.source_id}), "
                f"{attempt.status.value}, {attempt.result_count} additional items. "
                + attempt.explanation
            )
        if collection_pass.plan is not None:
            for task in collection_pass.plan.tasks:
                if task.selected:
                    lines.append(
                        f"Pass {index} terms for {task.source_id}: "
                        + ", ".join(task.terms)
                        + f" ({task.provenance})."
                    )
    return lines

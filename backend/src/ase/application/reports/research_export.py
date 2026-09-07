"""Shared frozen collection receipts, with no inference from empty or unavailable sources."""

from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.registry_identifiers import describe_lookup
from ase.domain.research_records import ResearchReceipt


def research_sections(receipt: ResearchReceipt | None) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if receipt is None:
        return (("Collection coverage", ("No collection receipt was saved for this version.",)),)
    period = (
        "Recorded project/acquisition/publication"
        if receipt.time_basis is EvidenceTimeBasis.RECORDED
        else "Acquisition/publication"
        if receipt.time_basis is EvidenceTimeBasis.RESEARCH
        else "Publication"
    )
    lines = [
        f"Policy: {receipt.policy_version}. Mode: {receipt.mode}; focus: {receipt.focus}.",
        f"Research question: {receipt.question}",
        f"{period} "
        f"window: {receipt.since.isoformat()} to {receipt.until.isoformat()} (end exclusive).",
        f"Requested languages: {', '.join(receipt.languages) or 'none recorded'}.",
        f"Planned search terms: {', '.join(receipt.terms) or 'none recorded'}.",
        f"Collected items: {receipt.collected_items} (new public collection). "
        "Selection for this report is a separate step.",
        f"{receipt.temporal_notice} Empty or unavailable sources do not "
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
        if plan.candidate_hypotheses:
            lines.append(
                "Candidate hypotheses are unverified search context, not established matches."
            )
            lines.extend(
                f"Candidate {row.id} ({row.origin}): {row.label}; "
                f"supplied identifiers: {', '.join(row.identifiers) or 'none'}."
                for row in plan.candidate_hypotheses
            )
        for task in plan.tasks:
            if task.selected:
                lines.append(
                    f"Selected task {task.source_name} ({task.source_id}): "
                    f"task {task.task_id or task.source_id}; purpose {task.purpose}; "
                    f"candidate {task.candidate_id or 'none'}; "
                    f"{task.provenance}; language {task.language or 'not specified'}; "
                    f"query language {task.query_language or 'original terms'}; "
                    f"terms: {', '.join(task.terms) or 'none supplied'}. {task.temporal_scope}"
                    + describe_lookup(task.registry_lookup)
                )
    if receipt.plan and receipt.plan.planning:
        trace = receipt.plan.planning
        lines.append(
            f"Automatic planning ({trace.policy_version}): {trace.status}; "
            f"requested model {trace.requested_model or 'none'}; "
            f"returned model {trace.returned_model or 'none'}; calls {trace.call_count}. "
            + trace.reason
        )
        lines.append("Accepted for collection is not proof of execution; consult attempt receipts.")
        lines.extend(
            f"Model-proposed candidate {row.id}: {row.label}; identifiers: {row.identifiers}."
            for row in trace.proposed_candidates
        )
        lines.extend(
            f"Model-proposed task model:{row.id}: {row.source_id}; {row.purpose}; "
            f"terms: {row.terms}; "
            f"accepted for collection: {'model:' + row.id in trace.accepted_task_ids}."
            for row in trace.proposed_tasks
        )
    if receipt.plan and receipt.plan.continuation:
        review = receipt.plan.continuation
        lines.append(
            f"Model collection review ({review.policy_version}): {review.decision}; "
            f"requested {review.requested_decision or 'unavailable'}; basis {review.basis}; "
            f"model {review.model or 'unavailable'}. "
            f"Reviewed {review.context_count} of {review.total_count} first-pass records. "
            "Unverified model judgement, not a confidence or truth score."
        )
        lines.append(review.rationale)
        if review.override_reason:
            lines.append("Decision override: " + review.override_reason)
        lines.extend("Unresolved gap: " + gap for gap in review.gaps)
        lines.extend(
            f"Review excerpt: {row.event_id}; {row.source_id}; hash {row.content_hash}; "
            f"{row.field}: {row.quote}"
            for row in review.citations
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
            f"task {attempt.task_id or attempt.source_id}; purpose {attempt.purpose}; "
            f"candidate {attempt.candidate_id or 'none'}; "
            f"{attempt.status.value.replace('_', ' ')}, {attempt.result_count} {count_kind}; "
            f"language {attempt.language or 'not recorded'}. {attempt.explanation}"
            + describe_lookup(attempt.registry_lookup)
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
                f"task {attempt.task_id or attempt.source_id}; purpose {attempt.purpose}; "
                f"{attempt.status.value}, {attempt.result_count} additional items. "
                + attempt.explanation
            )
        if collection_pass.plan is not None:
            for task in collection_pass.plan.tasks:
                if task.selected:
                    lines.append(
                        f"Pass {index} terms for {task.task_id or task.source_id}: "
                        + ", ".join(task.terms)
                        + f" ({task.provenance})."
                    )
    return lines

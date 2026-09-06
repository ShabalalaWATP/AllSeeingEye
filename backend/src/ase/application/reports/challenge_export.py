"""Shared plain-text challenge projection for all report export formats."""

from ase.domain.challenge import ReportChallenge


def challenge_sections(value: ReportChallenge | None) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if value is None:
        return ()
    sections = [
        (
            "Judgement challenge",
            (
                f"Method: {value.method_version}. "
                f"Shared collection limit: {value.request_limit} requests "
                f"and {value.seconds_limit} seconds across all initial judgements.",
                "Redrafted against changed selected evidence: "
                f"{'yes' if value.redrafted else 'no'}.",
                *value.limitations,
            ),
        )
    ]
    for row in value.searches:
        lines = [
            f"Initial statement: {row.statement}",
            f"Search status: {row.status.replace('_', ' ')}.",
            f"Contrary query phrases: {'; '.join(row.terms) or 'unavailable'}.",
            f"Collected items: {row.collected_items}; retained in final selection: "
            f"{len(row.selected_event_ids)}.",
        ]
        if row.explanation:
            lines.append(row.explanation)
        lines.extend(
            f"{attempt.source_name}: {attempt.status.value.replace('_', ' ')}; "
            f"{attempt.result_count} items. {attempt.explanation}"
            for attempt in row.attempts
        )
        sections.append((f"{row.judgement_id}: contrary collection", tuple(lines)))
    for review in value.reviews:
        lines = [f"Final statement: {review.statement}", f"Model review: {review.status}."]
        if review.explanation:
            lines.append(review.explanation)
        if review.advocacy:
            view = review.advocacy
            lines.extend(
                (
                    view.argument,
                    f"Model-cited evidence: {', '.join(view.evidence) or 'none'}.",
                    view.rationale,
                    f"Confidence before: {view.confidence_before or 'unchanged'}; "
                    f"after: {view.confidence_after or 'unchanged'}.",
                )
            )
        sections.append((f"{review.judgement_id}: contrarian view", tuple(lines)))
    return tuple(sections)

"""Export generated web context with native citation spans and explicit provenance."""

from ase.domain.web_research import WebResearchRecord


def web_context_sections(
    record: WebResearchRecord | None,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Text-only document export keeps context and every native citation inspectable."""
    if record is None:
        return ()
    lines = (
        record.notice,
        f"{record.status}: {record.explanation}",
        f"Retrieved {record.retrieved_at.isoformat()}; "
        f"model {record.returned_model or record.requested_model or 'unavailable'}; "
        f"requests {record.request_count}, web calls {record.tool_calls}.",
        *([record.synthesis] if record.synthesis else []),
        *(
            f"Provider citation [{row.start_index}:{row.end_index}]: {row.title}: {row.url}"
            for row in record.citations
        ),
    )
    return (("Fresh web context", lines),)

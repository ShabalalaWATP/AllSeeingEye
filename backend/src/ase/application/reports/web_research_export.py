"""Export generated web context with native citation spans and explicit provenance."""

from ase.application.reports.export_text import plain_markdown, safe_url
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


def web_context_markdown(record: WebResearchRecord | None) -> list[str]:
    if record is None:
        return []
    lines = [
        "## Fresh web context",
        "",
        plain_markdown(record.notice),
        "",
        plain_markdown(f"{record.status}: {record.explanation}"),
        "",
        plain_markdown(
            f"Retrieved {record.retrieved_at.isoformat()}. "
            f"Requested model: {record.requested_model or 'none'}; "
            f"returned model: {record.returned_model or 'none'}; "
            f"profile revision: {record.profile_revision or 'none'}. "
            f"Requests: {record.request_count}; web tool calls: {record.tool_calls}."
        ),
        "",
    ]
    if not record.synthesis:
        return lines
    cursor = 0
    chunks: list[str] = []
    for row in sorted(record.citations, key=lambda value: value.end_index):
        if row.end_index < cursor:
            continue
        chunks.append(plain_markdown(record.synthesis[cursor : row.end_index]))
        url = safe_url(row.url)
        if url:
            chunks.append(f" [{plain_markdown(row.title)}]({url}) ")
        cursor = row.end_index
    chunks.append(plain_markdown(record.synthesis[cursor:]))
    return [*lines, "".join(chunks), ""]

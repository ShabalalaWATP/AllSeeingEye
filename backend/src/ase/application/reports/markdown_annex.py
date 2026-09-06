"""Readable Markdown evidence index followed by complete frozen provenance."""

from collections.abc import Sequence

from ase.application.reports.export_text import evidence_metadata, plain_markdown, safe_url
from ase.domain.evidence import EvidenceItem, QualityOfInformation
from ase.domain.validation import Finding


def _link(value: str | None, label: str) -> str:
    url = safe_url(value)
    return f"[{label}]({url.replace('&', '&amp;')})" if url else "Unavailable"


def annex_lines(
    evidence: Sequence[EvidenceItem], quality: QualityOfInformation, findings: Sequence[Finding]
) -> list[str]:
    lines = ["## Quality of information", "", plain_markdown(quality.describe()), ""]
    if findings:
        lines += ["## Validator findings", ""]
        lines.extend(
            f"- {f.severity.value}: {plain_markdown(f.location)}: {plain_markdown(f.message)}"
            for f in findings
        )
        lines.append("")
    lines += [
        "## Evidence annex",
        "",
        "Frozen feed metadata and snippets. Source content and translations "
        "have not been independently verified.",
        "",
        "| Label | Grade | Source | Published | Title | Link | Archive |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in evidence:
        cells = [
            item.label,
            item.grade,
            item.source_name,
            item.published_at.strftime("%Y-%m-%d %H:%M"),
            item.title,
        ]
        lines.append(
            "| "
            + " | ".join(plain_markdown(value) for value in cells)
            + f" | {_link(item.url, 'link')} | {_link(item.archive_url, 'archive')} |"
        )
    lines.append("")
    if not evidence:
        lines += ["No frozen evidence.", ""]
    for item in evidence:
        lines += [
            f"### {plain_markdown(item.label)}",
            "",
            f"Original title: {plain_markdown(item.title)}",
        ]
        if item.title_en:
            lines.append(f"Translation (unverified): {plain_markdown(item.title_en)}")
        if item.summary:
            lines.append(f"Source snippet: {plain_markdown(item.summary)}")
        lines.extend(f"- {plain_markdown(line)}" for line in evidence_metadata(item))
        if item.flags:
            lines.append(f"- Flags: {plain_markdown('; '.join(item.flags))}")
        lines.append("")
    return lines

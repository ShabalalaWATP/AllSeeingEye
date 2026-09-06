"""Recover version-specific display dates without borrowing mutable record dates."""

import re
from datetime import UTC

from ase.domain.report_records import ReportRecord, ReportVersion

_PERIOD = re.compile(
    r"Template: [a-z_]+\. Period \d{4}-\d{2}-\d{2} \d{2}:\d{2} to "
    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC\. "
    r"Data cut-off \d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC\."
)


def frozen_period_line(record: ReportRecord, version: ReportVersion) -> str:
    """Use the saved engine header; missing legacy dates remain explicitly unknown."""
    start, end, cutoff = version.period_from, version.period_to, version.data_cutoff
    if (
        start is not None
        and end is not None
        and cutoff is not None
        and start.tzinfo is not None
        and end.tzinfo is not None
        and cutoff.tzinfo is not None
    ):
        return (
            f"Template: {record.template}. Period {start.astimezone(UTC):%Y-%m-%d %H:%M} to "
            f"{end.astimezone(UTC):%Y-%m-%d %H:%M} UTC. "
            f"Data cut-off {cutoff.astimezone(UTC):%Y-%m-%d %H:%M} UTC."
        )
    for line in version.markdown.splitlines():
        # Template identifiers may contain Markdown-escaped underscores. Normalise
        # only this known escape before matching the complete engine-owned line.
        candidate = line.replace("\\_", "_")
        if _PERIOD.fullmatch(candidate):
            return candidate
    return (
        f"Template: {record.template}. Reporting period and data cut-off: unknown "
        f"(not captured in this version). Created: {version.created_at.isoformat()}."
    )

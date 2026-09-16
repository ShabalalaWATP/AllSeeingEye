"""Reuse frozen evidence without reconstructing or regrading historical sources."""

from dataclasses import replace

from ase.application.reports.selection import Selection
from ase.domain.evidence import EvidenceItem

REUSE_NOTICE = (
    "Previously saved evidence is retained context with its original dates, grades and provenance. "
    "Do not describe historical material as newly collected or as current-period reporting. "
    "Local evidence labels have changed; use only the final labels supplied in this prompt. "
    "The evidence limit may leave newly collected items outside the final selection."
)


def with_reused_evidence(selected: Selection, reused: tuple[EvidenceItem, ...]) -> Selection:
    if not reused:
        return selected
    # Existing grades, provenance and timestamps remain frozen. Labels alone are local
    # to the new report. The final prompt describes earlier dates as retained context.
    rows = {row.event_id: row for row in reused}
    for row in selected.items:
        if row.event_id not in rows and len(rows) < 100:
            rows[row.event_id] = row
    if len(rows) > 100:
        raise ValueError("Frozen reuse exceeds the report evidence limit")
    return Selection(
        tuple(replace(row, label=f"E{index}") for index, row in enumerate(rows.values(), 1)),
        selected.flagged,
        max(selected.considered, len(rows)),
        selected.merged,
    )

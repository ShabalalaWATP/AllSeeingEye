"""An incomplete section pauses the job without discarding its validated checkpoints."""

from ase.application.reports.drafting import Draft
from ase.domain.validation import Finding, Severity


class SectionIncomplete(Exception):
    def __init__(self, section_id: str, reason: str, draft: Draft) -> None:
        super().__init__(
            "Report drafting is incomplete. Saved sections are available for review or resumption."
        )
        self.section_id = section_id
        self.reason = reason
        self.draft = draft
        draft.findings.append(Finding("section_incomplete", Severity.ERROR, section_id, str(self)))


class StepExhausted(Exception):
    """Internal control flow after the paid attempt and safe checkpoint were recorded."""

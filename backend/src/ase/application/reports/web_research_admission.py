"""Remove generated public web context when source permission is unavailable."""

from dataclasses import replace

from ase.application.ports.source_controls import SourceAdmission
from ase.application.source_admission import source_denial_reason
from ase.domain.web_research import WEB_SOURCE_ID, WebResearchRecord


def unavailable_web_context(
    record: WebResearchRecord, admission: SourceAdmission
) -> WebResearchRecord:
    return replace(
        record,
        status="unavailable",
        synthesis="",
        citations=(),
        consulted_urls=(),
        explanation=source_denial_reason(
            admission,
            WEB_SOURCE_ID,
            "The administrator disabled fresh web search. No web context was admitted.",
        ),
    )

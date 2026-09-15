"""Checks URLs and hedge vocabulary in model-authored report prose."""

from collections.abc import Mapping

from ase.domain.doctrine import find_hedges, find_urls
from ase.domain.reports import ReportBody
from ase.domain.validation_types import Finding, Severity


def check_prose(
    body: ReportBody, evidence_urls: Mapping[str, str | None], findings: list[Finding]
) -> None:
    cited = body.cited_labels()
    allowed = {url for label, url in evidence_urls.items() if url and label in cited}
    for text in body.texts():
        for url in find_urls(text):
            if url.rstrip(".,") not in allowed:
                findings.append(
                    Finding(
                        "url", Severity.ERROR, "text", f"URL not from cited evidence: {url[:80]}"
                    )
                )
    hedged = [text for text in body.texts() if find_hedges(text)]
    if hedged:
        findings.append(
            Finding(
                "hedge",
                Severity.WARNING,
                "text",
                f"{len(hedged)} passage(s) use hedge words; "
                "check they describe capability, not likelihood",
            )
        )

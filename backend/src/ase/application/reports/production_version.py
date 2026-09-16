"""Assemble final provenance, citation checks and the frozen report version."""

import asyncio
from uuid import uuid4

from ase.application.ports.evidence_urls import EvidenceUrlResolver
from ase.application.ports.report_export import AsyncReportProjector
from ase.application.reports.citation_checks import check_generated_report_citations
from ase.application.reports.document import build_document
from ase.application.reports.drafting import Draft
from ase.application.reports.post_draft_checks import mechanical_quality_findings
from ase.application.reports.post_draft_doctrine import check_analytical_prose
from ase.application.reports.production_types import Job, Totals
from ase.application.reports.progress import Progress, reached
from ase.application.reports.publication_markdown import render_document_markdown
from ase.application.reports.quality_gate import final_report_status
from ase.application.reports.resolve_links import resolve_cited_links
from ase.application.reports.sections.quality import ensure_requirement_coverage
from ase.application.reports.selection import Selection
from ase.application.reports.source_assessment_projection import capture_unassessed_report_sources
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.challenge import ReportChallenge
from ase.domain.direction import Direction
from ase.domain.evidence import quality_of_information
from ase.domain.judgement_assessment import build_report_assessment
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.reports import ReportBody, ReportHeader, ReportStatus
from ase.domain.research_context import build_research_context
from ase.domain.research_records import ResearchReceipt
from ase.domain.research_runs import ResearchStage
from ase.domain.validation import Severity, validate_body


def header_for(job: Job, selection: Selection, direction: Direction | None) -> ReportHeader:
    return ReportHeader(
        template=job.template.id,
        title=job.title,
        scope=job.scope,
        period_from=job.period_from,
        period_to=job.period_to,
        data_cutoff=max((job.now, *(item.captured_at for item in selection.items))),
        requirements=(
            tuple(row.id for row in job.request.canonical_requirements)
            if job.request.canonical_requirements
            else direction.requirement_ids()
            if direction
            else ()
        ),
    )


async def build_version(
    job: Job,
    draft: Draft,
    body: ReportBody,
    selection: Selection,
    totals: Totals,
    *,
    direction: Direction | None,
    receipt: ResearchReceipt | None,
    advocacy: DevilsAdvocacy | None,
    challenge: ReportChallenge | None,
    url_resolver: EvidenceUrlResolver | None,
    progress: Progress | None,
    projector: AsyncReportProjector | None = None,
) -> ReportVersion:
    evidence = selection.items
    quality = quality_of_information(evidence, selection.flagged)
    header = header_for(job, selection, direction)
    body, coverage_findings = ensure_requirement_coverage(
        body,
        direction,
        supported=draft.supported_requirements,
        requirements=job.request.canonical_requirements,
    )
    for finding in coverage_findings:
        if finding not in totals.findings:
            totals.findings.append(finding)
    # Challenge and advocacy can change a validated draft, including on resumed jobs.
    # Recheck the final prose without reapplying evidence-derived confidence rewrites.
    # The frozen packet does not yet contain exact original-passage links or typed
    # forecast fields, so neither is inferred from prose here.
    final_validation = validate_body(
        body,
        frozenset(item.label for item in evidence),
        {item.label: item.url for item in evidence},
        previous_exists=job.previous is not None or bool(job.followup_judgements),
    )
    final_findings = (
        *final_validation.findings,
        *check_analytical_prose(body),
        *mechanical_quality_findings(body, header, job.template, evidence),
    )
    for finding in final_findings:
        if finding not in totals.findings:
            totals.findings.append(finding)
    base_status = (
        ReportStatus.FAILED
        if draft.body is None
        else ReportStatus.NEEDS_REVIEW
        if draft.has_errors
        or coverage_findings
        or any(finding.severity is Severity.ERROR for finding in final_findings)
        else ReportStatus.READY
    )
    if url_resolver is not None:
        cited = body.cited_labels() | frozenset(advocacy.evidence if advocacy else ())
        if challenge:
            cited |= challenge.cited_labels()
        evidence = await resolve_cited_links(url_resolver, evidence, cited)
    await reached(progress, ResearchStage.VALIDATING)
    assessment = build_report_assessment(body, evidence, totals.findings)
    citation_checks = check_generated_report_citations(body, evidence)
    status = final_report_status(
        base_status, assessment, citation_checks, challenge, totals.findings
    )
    research_context = build_research_context(evidence) if receipt else None
    version_id = job.version_id or uuid4()
    # This is the effective capture cutoff, which may follow the job's start time.
    source_assessment = capture_unassessed_report_sources(
        version_id, body, evidence, frozen_at=header.data_cutoff
    )
    version = ReportVersion(
        id=version_id,
        report_id=job.report_id or uuid4(),
        number=job.previous.number + 1 if job.previous is not None else 1,
        status=status,
        body=body,
        findings=tuple(totals.findings),
        evidence=evidence,
        quality=quality,
        assessment=assessment,
        source_assessment=source_assessment,
        markdown="",
        profile_id=job.profile.id,
        model=draft.model or job.profile.model,
        prompt_tokens=totals.prompt_tokens,
        completion_tokens=totals.completion_tokens,
        latency_ms=totals.latency_ms,
        attempts=draft.attempts,
        created_at=job.now,
        period_from=header.period_from,
        period_to=header.period_to,
        data_cutoff=header.data_cutoff,
        direction=direction,
        canonical_requirements=job.request.canonical_requirements,
        document_schema_version=2,
        advocacy=advocacy,
        research=receipt,
        citation_checks=citation_checks,
        challenge=challenge,
        research_context=research_context,
    )
    record = ReportRecord(
        id=version.report_id,
        template=job.template.id,
        title=job.title,
        scope=job.scope,
        period_from=header.period_from,
        period_to=header.period_to,
        data_cutoff=header.data_cutoff,
        status=status,
        created_by=job.actor.id,
        created_at=job.now,
        latest_version=version.number,
        team_id=job.request.team_id,
    )
    document = (
        await projector.build(record, version)
        if projector is not None
        else await asyncio.to_thread(build_document, record, version)
    )
    version.markdown = render_document_markdown(document)
    return version

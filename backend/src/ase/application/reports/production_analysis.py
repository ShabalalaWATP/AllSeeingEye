"""Run the dedicated analysis pass for one version and account for its single call."""

from __future__ import annotations

from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.reports.analysis import run_analysis
from ase.application.reports.production_checkpoint import ProductionCheckpoints
from ase.application.reports.production_types import Job, Totals, usage_entry
from ase.application.reports.production_version import header_for
from ase.application.reports.selection import Selection
from ase.domain.direction import Direction
from ase.domain.reports import ReportBody


async def analyse_body(
    job: Job,
    gateway: LlmGateway,
    cipher: SecretCipher,
    body: ReportBody,
    selection: Selection,
    direction: Direction | None,
    totals: Totals,
    checkpoints: ProductionCheckpoints | None,
) -> ReportBody:
    """The dedicated analysis pass, metered like every other call and never fatal."""
    outcome = await run_analysis(
        gateway,
        job.profile,
        cipher.decrypt(job.profile.api_key_encrypted),
        job.template,
        header_for(job, selection, direction),
        body,
        selection.items,
        question=job.request.question,
        background=job.background,
        checkpoints=checkpoints.section_checkpoints if checkpoints is not None else None,
    )
    if outcome.attempts:
        totals.usage.append(
            usage_entry(
                job,
                job.profile,
                f"report:{job.template.id}:analysis",
                outcome.performed,
                outcome,
            )
        )
        totals.add(
            outcome.prompt_tokens,
            outcome.completion_tokens,
            outcome.latency_ms,
            outcome.findings,
        )
    else:
        totals.findings.extend(outcome.findings)
    return outcome.apply(body)

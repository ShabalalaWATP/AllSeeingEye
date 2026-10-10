"""Draft one selection and account for exactly the calls made by that draft."""

from functools import partial

from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.reports.drafting import Draft, draft_body
from ase.application.reports.production_checkpoint import ProductionCheckpoints
from ase.application.reports.production_types import Job, Totals, usage_entry
from ase.application.reports.production_version import header_for
from ase.application.reports.progress import Progress, reached
from ase.application.reports.reused_evidence import REUSE_NOTICE
from ase.application.reports.sections import draft_sections
from ase.application.reports.selection import Selection
from ase.application.reports.subscription_updates import update_guidance
from ase.domain.direction import Direction
from ase.domain.evidence import quality_of_information
from ase.domain.research_records import ResearchReceipt
from ase.domain.research_runs import ResearchStage


async def draft_for_job(
    selected: Selection,
    *,
    job: Job,
    gateway: LlmGateway,
    cipher: SecretCipher,
    direction: Direction | None,
    receipt: ResearchReceipt | None,
    original_context: str,
    totals: Totals,
    checkpoints: ProductionCheckpoints | None,
    progress: Progress | None,
) -> Draft:
    earlier = (
        job.previous.body.key_judgements if job.previous is not None else job.followup_judgements
    )

    await reached(progress, ResearchStage.DRAFTING)
    draft_fn = (
        draft_body
        if checkpoints is None
        else partial(
            draft_sections,
            checkpoints=checkpoints.section_checkpoints,
        )
    )
    draft = await draft_fn(
        gateway,
        job.profile,
        cipher.decrypt(job.profile.api_key_encrypted),
        job.template,
        header_for(job, selected, direction),
        job.request.question,
        quality_of_information(selected.items, selected.flagged),
        selected.items,
        earlier,
        direction=direction,
        canonical_requirements=job.request.canonical_requirements,
        background="\n\n".join(
            filter(
                None,
                (
                    job.background,
                    receipt.describe() if receipt else None,
                    original_context,
                    REUSE_NOTICE
                    if job.reused_evidence and job.request.alert_origin is None
                    else None,
                    update_guidance(
                        job.subscription_baseline,
                        selected.items,
                        frozenset(job.request.subscription_seen_signatures),
                        previous_missing=job.request.subscription_previous_report_id is not None
                        and job.subscription_baseline is None,
                    ),
                ),
            )
        )
        or None,
    )
    totals.usage.append(
        usage_entry(job, job.profile, f"report:{job.template.id}", draft.body is not None, draft)
    )
    totals.add(draft.prompt_tokens, draft.completion_tokens, draft.latency_ms, draft.findings)
    return draft

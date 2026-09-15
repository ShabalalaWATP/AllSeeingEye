"""Directional planning and optional advocacy, with explicit model accounting."""

from collections.abc import Sequence

from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.reports.advocacy import advocate, apply_advocacy
from ase.application.reports.direction import direct
from ase.application.reports.production_types import Job, ProfileLookup, Totals, usage_entry
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.direction import Direction
from ase.domain.evidence import EvidenceItem
from ase.domain.llm import LlmRole
from ase.domain.reports import ReportBody
from ase.domain.validation import Finding, Severity


async def direct_for_job(
    job: Job,
    profile_for: ProfileLookup,
    totals: Totals,
    gateway: LlmGateway,
    cipher: SecretCipher,
) -> Direction | None:
    if job.direction is not None:
        return job.direction
    question = (job.request.question or "").strip()
    if not (job.template.needs_question or job.request.research_mode) or not question:
        return None
    profile = await profile_for(LlmRole.DIRECTION)
    if profile is None:
        totals.findings.append(
            Finding(
                "direction",
                Severity.WARNING,
                "direction",
                "No enabled model profile plays the direction role; evidence was "
                "selected without search terms.",
            )
        )
        return None
    key = cipher.decrypt(profile.api_key_encrypted)
    draft = await direct(
        gateway,
        profile,
        key,
        question,
        job.country_name,
        languages=job.request.research_languages if job.request.research_mode else (),
    )
    purpose = f"report:{job.template.id}:direction"
    totals.usage.append(usage_entry(job, profile, purpose, draft.direction is not None, draft))
    totals.add(draft.prompt_tokens, draft.completion_tokens, draft.latency_ms, draft.findings)
    return draft.direction


async def advocate_for_job(
    job: Job,
    profile_for: ProfileLookup,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    totals: Totals,
    gateway: LlmGateway,
    cipher: SecretCipher,
) -> tuple[ReportBody, DevilsAdvocacy | None]:
    profile = await profile_for(LlmRole.DEVIL)
    if profile is None:
        totals.findings.append(
            Finding(
                "advocacy",
                Severity.WARNING,
                "devils_advocacy",
                "No enabled model profile plays the devil role; no contrarian view was taken.",
            )
        )
        return body, None
    key = cipher.decrypt(profile.api_key_encrypted)
    draft = await advocate(gateway, profile, key, body, evidence)
    purpose = f"report:{job.template.id}:advocacy"
    totals.usage.append(usage_entry(job, profile, purpose, draft.advocacy is not None, draft))
    totals.add(draft.prompt_tokens, draft.completion_tokens, draft.latency_ms, draft.findings)
    if draft.advocacy is None:
        return body, None
    return apply_advocacy(body, draft.advocacy)

"""Directional planning and optional advocacy, with explicit model accounting."""

from collections.abc import Sequence

from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.reports.advocacy import advocate, apply_advocacy
from ase.application.reports.contradiction_pass import contested, explain_contradictions
from ase.application.reports.direction import direct
from ase.application.reports.entailment import check_entailment
from ase.application.reports.production_types import Job, ProfileLookup, Totals, usage_entry
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.direction import Direction
from ase.domain.evidence import EvidenceItem
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.report_quality_rules import CONTRADICTION_RULE, ENTAILMENT_RULE
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


async def _review_profile(profile_for: ProfileLookup) -> LlmProfile | None:
    return await profile_for(LlmRole.ASSESSMENT)


async def explain_for_job(
    job: Job,
    profile_for: ProfileLookup,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    totals: Totals,
    gateway: LlmGateway,
    cipher: SecretCipher,
) -> None:
    """Explain a cited disagreement, or leave the mechanical naming of it to stand."""
    if not contested(body):
        return
    profile = await _review_profile(profile_for)
    if profile is None:
        totals.findings.append(
            Finding(
                CONTRADICTION_RULE,
                Severity.WARNING,
                "key_judgements",
                "No enabled model profile plays the assessment role, so the cited "
                "disagreement was not explained. The sources and their grades are "
                "still named.",
            )
        )
        return
    draft = await explain_contradictions(
        gateway, profile, cipher.decrypt(profile.api_key_encrypted), body, evidence
    )
    purpose = f"report:{job.template.id}:contradiction"
    totals.usage.append(usage_entry(job, profile, purpose, draft.ran, draft))
    totals.add(draft.prompt_tokens, draft.completion_tokens, draft.latency_ms, draft.findings)
    for finding in draft.reasons:
        if finding not in totals.findings:
            totals.findings.append(finding)


async def entail_for_job(
    job: Job,
    profile_for: ProfileLookup,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    totals: Totals,
    gateway: LlmGateway,
    cipher: SecretCipher,
) -> None:
    """Run the bounded entailment pass, or record plainly that it could not run."""
    if not body.key_judgements:
        return
    profile = await _review_profile(profile_for)
    if profile is None:
        totals.findings.append(
            Finding(
                ENTAILMENT_RULE,
                Severity.WARNING,
                "key_judgements",
                "No enabled model profile plays the assessment role, so the entailment "
                "check on the key judgements did not run. Citations were checked "
                "literally only.",
            )
        )
        return
    draft = await check_entailment(
        gateway, profile, cipher.decrypt(profile.api_key_encrypted), body, evidence
    )
    purpose = f"report:{job.template.id}:entailment"
    totals.usage.append(usage_entry(job, profile, purpose, draft.ran, draft))
    totals.add(draft.prompt_tokens, draft.completion_tokens, draft.latency_ms, draft.findings)
    for finding in draft.reasons:
        if finding not in totals.findings:
            totals.findings.append(finding)

"""Review a resumable report without changing its checkpointed evidence labels."""

from dataclasses import replace

from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.reports.advocacy import apply_advocacy
from ase.application.reports.challenge_models import challenge_call
from ase.application.reports.production_types import Job, ProfileLookup, Totals, usage_entry
from ase.application.reports.progress import Progress, reached
from ase.application.reports.selection import Selection
from ase.domain.challenge import ChallengeReview, ChallengeSearch, ReportChallenge
from ase.domain.llm import LlmRole
from ase.domain.reports import Gap, ReportBody
from ase.domain.research_runs import ResearchStage
from ase.domain.validation import Finding, Severity

FROZEN_COLLECTION_GAP = (
    "This resumable run reviews the frozen evidence. Additional contrary-source collection "
    "was not performed after drafting, so counterevidence coverage remains incomplete."
)


async def review_frozen(
    job: Job,
    body: ReportBody,
    selection: Selection,
    *,
    gateway: LlmGateway,
    cipher: SecretCipher,
    profile_for: ProfileLookup,
    totals: Totals,
    progress: Progress | None,
    searches: tuple[ChallengeSearch, ...] | None = None,
    redrafted: bool = False,
) -> tuple[ReportBody, ReportChallenge]:
    """Review the final frozen packet, including truthful optional source receipts."""
    await reached(progress, ResearchStage.CHALLENGING)
    profile = await profile_for(LlmRole.DEVIL) or await profile_for(LlmRole.DIRECTION)
    reviews: tuple[ChallengeReview, ...] = ()
    if profile is not None and body.key_judgements:
        result = await challenge_call(
            gateway,
            profile,
            cipher.decrypt(profile.api_key_encrypted),
            body,
            evidence=selection.items,
            languages=job.request.research_languages,
            review=True,
        )
        totals.usage.append(
            usage_entry(
                job,
                profile,
                f"report:{job.template.id}:challenge:reviews",
                result.succeeded,
                result,
            )
        )
        totals.add(
            result.prompt_tokens, result.completion_tokens, result.latency_ms, result.findings
        )
        reviews = result.reviews
    if not reviews:
        reviews = tuple(
            ChallengeReview(
                row.id,
                row.statement,
                "unavailable",
                explanation="No usable all-judgement model review was available.",
            )
            for row in body.key_judgements
        )
    adjusted = []
    for review in reviews:
        adjusted_review = review
        if review.advocacy is not None:
            body, advocacy = apply_advocacy(body, review.advocacy)
            adjusted_review = replace(review, advocacy=advocacy)
        adjusted.append(adjusted_review)
    gap = (
        FROZEN_COLLECTION_GAP
        if searches is None
        else "Some judgements had no targeted fresh counterevidence search. "
        "An empty or failed search does not confirm a judgement."
        if any(row.status != "attempted" for row in searches)
        else "Fresh source searches were attempted. Returned candidates were reviewed "
        "without treating model agreement or an empty result as independent corroboration."
    )
    totals.findings.append(Finding("challenge", Severity.WARNING, "challenge", gap))
    body = replace(body, gaps=(*body.gaps, Gap(gap)))
    return body, ReportChallenge(
        searches=searches
        if searches is not None
        else tuple(
            ChallengeSearch(
                row.id,
                row.statement,
                (),
                "unavailable",
                explanation=FROZEN_COLLECTION_GAP,
            )
            for row in body.key_judgements
        ),
        reviews=tuple(adjusted),
        redrafted=redrafted,
    )

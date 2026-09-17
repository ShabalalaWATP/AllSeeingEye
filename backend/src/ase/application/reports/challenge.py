"""Challenge every initial judgement privately, then review the final selected draft."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace

from ase.application.ports.feeds import EventStore
from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.ports.research import ResearchCollection
from ase.application.reports.advocacy import apply_advocacy
from ase.application.reports.challenge_models import ChallengeModelDraft, challenge_call
from ase.application.reports.drafting import Draft
from ase.application.reports.production_types import Job, ProfileLookup, Totals, usage_entry
from ase.application.reports.progress import Progress, reached
from ase.application.reports.selection import Selection
from ase.domain.challenge import ChallengeReview, ChallengeSearch, ReportChallenge
from ase.domain.errors import RateLimited
from ase.domain.llm import LlmProfile, LlmRole
from ase.domain.project_lookup import preserve_project_lookup
from ase.domain.reports import ReportBody
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery
from ase.domain.research_runs import ResearchStage
from ase.domain.validation import Finding, Severity


@dataclass(frozen=True, slots=True)
class ChallengeOutcome:
    draft: Draft
    selection: Selection
    body: ReportBody
    challenge: ReportChallenge

    @property
    def parts(self) -> tuple[Draft, Selection, ReportBody, ReportChallenge]:
        """The four values a caller resumes the pipeline with, in pipeline order."""
        return self.draft, self.selection, self.body, self.challenge


async def run_challenge(
    job: Job,
    initial: Draft,
    selection: Selection,
    *,
    query: ResearchQuery,
    store: EventStore,
    collection: ResearchCollection | None,
    gateway: LlmGateway,
    cipher: SecretCipher,
    profile_for: ProfileLookup,
    totals: Totals,
    select: Callable[[tuple[str, ...]], Selection],
    redraft: Callable[[Selection], Awaitable[Draft]],
    progress: Progress | None = None,
) -> ChallengeOutcome:
    """No shared-store writes or persistence; budgets belong to one challenge_many call."""
    body = initial.body or ReportBody()
    profile = await profile_for(LlmRole.DEVIL) or await profile_for(LlmRole.DIRECTION)
    plan = ChallengeModelDraft()

    async def model_call(target: ReportBody, *, review: bool = False) -> ChallengeModelDraft:
        if profile is None:
            return ChallengeModelDraft()
        await reached(progress, ResearchStage.CHALLENGING)
        result = await challenge_call(
            gateway,
            profile,
            cipher.decrypt(profile.api_key_encrypted),
            target,
            evidence=selection.items if review else (),
            languages=query.languages,
            review=review,
        )
        _account(job, profile, totals, result, "reviews" if review else "plan")
        return result

    area_search = query.area is not None
    # Current spatial adapters search catalogue coverage, not contrary text. Changing
    # terms would repeat the same area request without searching for disconfirmation.
    if profile is not None and body.key_judgements and not area_search:
        plan = await model_call(body)
    targets = tuple(row for row in body.key_judgements if row.id in plan.plans)
    batches: tuple[ResearchBatch, ...] = ()
    effective_terms: dict[str, tuple[str, ...]] = {}
    private_input = query.focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA)
    if targets and collection is not None and not private_input and not area_search:
        try:
            queries = tuple(
                replace(query, terms=preserve_project_lookup(query.terms, plan.plans[row.id]))
                for row in targets
            )
            effective_terms = {
                row.id: task.terms for row, task in zip(targets, queries, strict=True)
            }
            await reached(progress, ResearchStage.COLLECTING)
            batches = await collection.challenge_many(queries)
            if len(batches) != len(queries):
                raise ValueError("Incomplete challenge collection receipts")
        except (ValueError, AttributeError, RateLimited):
            batches = ()
            totals.findings.append(
                Finding(
                    "challenge",
                    Severity.WARNING,
                    "challenge",
                    "Bounded challenge collection is unavailable or busy; "
                    "existing evidence is retained.",
                )
            )
    found = {row.id: batch for row, batch in zip(targets, batches, strict=False)}
    searches = tuple(
        _search(row.id, row.statement, plan, found, effective_terms) for row in body.key_judgements
    )
    searches = tuple(
        replace(
            row,
            status="unavailable",
            explanation="Contrary collection within this area is unavailable. "
            "Spatial catalogue coverage is not a term-based contrary search. "
            "Model review uses the collected evidence.",
        )
        if area_search
        else replace(
            row,
            explanation="Public contrary search is disabled for private "
            "document and media inputs. Model review uses supplied evidence.",
        )
        if private_input
        else row
        for row in searches
    )
    initial_selection = selection
    for batch in batches:
        store.upsert(batch.items)
    if any(batch.items for batch in batches):
        candidate = select(tuple(term for terms in plan.plans.values() for term in terms))
        if _identity(candidate) != _identity(selection):
            revised = await redraft(candidate)
            if revised.body is not None:
                initial, selection, body = revised, candidate, revised.body
            else:
                # Failed replacement output is a stage warning, not a validation
                # error in the retained, separately validated original body.
                for finding in revised.findings:
                    if finding in totals.findings:
                        totals.findings.remove(finding)
                totals.findings.append(
                    Finding(
                        "challenge",
                        Severity.WARNING,
                        "challenge",
                        "Redrafting failed. The initial body and its original "
                        "evidence labels were retained.",
                    )
                )
    selected_ids = frozenset(item.event_id for item in selection.items)
    searches = tuple(
        replace(
            search,
            selected_event_ids=tuple(
                item.id for item in found[search.judgement_id].items if item.id in selected_ids
            ),
        )
        if search.judgement_id in found
        else search
        for search in searches
    )
    review_draft = await model_call(body, review=True) if profile and body.key_judgements else None
    reviews = (
        review_draft.reviews
        if review_draft and review_draft.reviews
        else tuple(
            ChallengeReview(
                row.id,
                row.statement,
                "unavailable",
                explanation="No usable all-judgement model review was available.",
            )
            for row in body.key_judgements
        )
    )
    body, adjusted_reviews = _apply_reviews(body, reviews)
    if any(row.status != "completed" for row in reviews) or any(
        row.status != "attempted" for row in searches
    ):
        totals.findings.append(
            Finding(
                "challenge",
                Severity.WARNING,
                "challenge",
                "Some judgement searches or reviews were unavailable; see receipts.",
            )
        )
    challenge = ReportChallenge(
        searches, tuple(adjusted_reviews), selection is not initial_selection
    )
    return ChallengeOutcome(initial, selection, body, challenge)


def _apply_reviews(
    body: ReportBody, reviews: tuple[ChallengeReview, ...]
) -> tuple[ReportBody, tuple[ChallengeReview, ...]]:
    adjusted_reviews = []
    for review in reviews:
        if review.advocacy:
            body, adjusted = apply_advocacy(body, review.advocacy)
            adjusted_reviews.append(replace(review, advocacy=adjusted))
        else:
            adjusted_reviews.append(review)
    return body, tuple(adjusted_reviews)


def _identity(selection: Selection) -> tuple[tuple[str, str, str], ...]:
    return tuple((row.label, row.event_id, row.content_hash) for row in selection.items)


def _search(
    target: str,
    statement: str,
    plan: ChallengeModelDraft,
    batches: dict[str, ResearchBatch],
    effective_terms: dict[str, tuple[str, ...]],
) -> ChallengeSearch:
    terms = effective_terms.get(target, plan.plans.get(target, ()))
    if not terms:
        return ChallengeSearch(
            target,
            statement,
            (),
            "plan_missing",
            explanation="No valid contrary query plan was available for this judgement.",
        )
    batch = batches.get(target)
    if batch is None:
        return ChallengeSearch(
            target,
            statement,
            terms,
            "unavailable",
            explanation="Bounded challenge collection was unavailable or busy. "
            "Existing evidence is retained.",
        )
    admitted = {
        CollectionStatus.COMPLETED,
        CollectionStatus.EMPTY,
        CollectionStatus.FAILED,
        CollectionStatus.TIMED_OUT,
    }
    if not any(row.status in admitted for row in batch.attempts) and not batch.items:
        exhausted = any(row.status is CollectionStatus.BUDGET_EXHAUSTED for row in batch.attempts)
        return ChallengeSearch(
            target,
            statement,
            terms,
            "budget_exhausted" if exhausted else "unavailable",
            batch.attempts,
            explanation="No completed search coverage was available; see source receipts.",
        )
    return ChallengeSearch(target, statement, terms, "attempted", batch.attempts, len(batch.items))


def _account(
    job: Job, profile: LlmProfile, totals: Totals, draft: ChallengeModelDraft, stage: str
) -> None:
    totals.usage.append(
        usage_entry(
            job, profile, f"report:{job.template.id}:challenge:{stage}", draft.succeeded, draft
        )
    )
    totals.add(draft.prompt_tokens, draft.completion_tokens, draft.latency_ms, draft.findings)

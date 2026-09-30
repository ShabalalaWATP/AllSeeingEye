"""Choose the checkpoint-aware challenge or advocacy stage for one report draft."""

from collections.abc import Awaitable, Callable, Mapping

from ase.application.ports.feeds import EventStore
from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.ports.research import (
    CheckpointedChallengeCollection,
    ResearchCollection,
    SourceOperationCheckpoints,
)
from ase.application.reports.challenge import run_challenge
from ase.application.reports.challenge_expansion import expand_and_review
from ase.application.reports.drafting import Draft
from ase.application.reports.frozen_challenge import review_frozen
from ase.application.reports.production_checkpoint import (
    ExpansionCheckpoints,
    ProductionCheckpoints,
    ProductionSnapshot,
)
from ase.application.reports.production_model_roles import advocate_for_job
from ase.application.reports.production_types import Job, ProfileLookup, Totals
from ase.application.reports.progress import Progress, reached
from ase.application.reports.selection import Selection
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.challenge import ReportChallenge
from ase.domain.grading import SourceProfile
from ase.domain.reports import ReportBody
from ase.domain.research import ResearchQuery
from ase.domain.research_runs import ResearchStage


async def review_for_job(
    job: Job,
    draft: Draft,
    selection: Selection,
    *,
    query: ResearchQuery | None,
    snapshot: ProductionSnapshot | None,
    source_operations: SourceOperationCheckpoints | None,
    checkpoints: ProductionCheckpoints | None,
    collection: ResearchCollection | None,
    profiles: Mapping[str, SourceProfile],
    store: EventStore,
    gateway: LlmGateway,
    cipher: SecretCipher,
    profile_for: ProfileLookup,
    totals: Totals,
    select: Callable[[tuple[str, ...]], Selection],
    redraft: Callable[[Selection], Awaitable[Draft]],
    progress: Progress | None,
) -> tuple[Draft, Selection, ReportBody, DevilsAdvocacy | None, ReportChallenge | None]:
    body = draft.body or ReportBody()
    advocacy: DevilsAdvocacy | None = None
    challenge = None
    if (
        query is not None
        and query.mode.requires_challenge
        and snapshot is not None
        and source_operations is not None
        and isinstance(checkpoints, ExpansionCheckpoints)
    ):
        outcome = await expand_and_review(
            job,
            draft,
            snapshot,
            collection=collection
            if isinstance(collection, CheckpointedChallengeCollection)
            else None,
            source_operations=source_operations,
            checkpoints=checkpoints,
            profiles=profiles,
            gateway=gateway,
            cipher=cipher,
            profile_for=profile_for,
            totals=totals,
            redraft=redraft,
            progress=progress,
        )
        draft, selection, body, challenge = outcome.parts
        advocacy = next((row.advocacy for row in challenge.reviews if row.advocacy), None)
    elif query is not None and query.mode.requires_challenge and checkpoints is not None:
        body, challenge = await review_frozen(
            job,
            body,
            selection,
            gateway=gateway,
            cipher=cipher,
            profile_for=profile_for,
            totals=totals,
            progress=progress,
        )
        advocacy = next((row.advocacy for row in challenge.reviews if row.advocacy), None)
    elif query is not None and query.mode.requires_challenge:
        original_findings = tuple(draft.findings)
        outcome = await run_challenge(
            job,
            draft,
            selection,
            query=query,
            store=store,
            collection=collection,
            gateway=gateway,
            cipher=cipher,
            profile_for=profile_for,
            totals=totals,
            select=select,
            redraft=redraft,
            progress=progress,
        )
        if outcome.challenge.redrafted:
            for finding in original_findings:
                if finding in totals.findings:
                    totals.findings.remove(finding)
        draft, selection, body, challenge = outcome.parts
        advocacy = next((row.advocacy for row in challenge.reviews if row.advocacy), None)
    elif job.request.devils_advocacy and body.key_judgements and draft.body is not None:
        await reached(progress, ResearchStage.CHALLENGING)
        body, advocacy = await advocate_for_job(
            job, profile_for, body, selection.items, totals, gateway, cipher
        )
    return draft, selection, body, advocacy, challenge

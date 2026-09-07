"""Real guarded monitor/claim mutations for observation and contention acceptance."""

from annotation_comparison_helpers import prepared
from ase.application.reports.claims import ClaimInput
from ase.domain.claim_revisions import ClaimCitationInput, ClaimReviewState
from team_helpers import CONTEXT


async def seeded(client, container, user, *, notify=True):
    actor, report, version, claim, request = await prepared(client, container, user)
    async with container.session_factory() as session:
        monitor = await container.annotation_monitors(session).create(
            actor, "Selected claim watch", request.before, ("claim",), notify
        )
    return actor, report, version, claim, monitor


async def correct(
    container,
    actor,
    previous,
    *,
    state=ClaimReviewState.REVIEWED,
    reason="Reviewed captured assertion.",
    conflicts=None,
):
    value = ClaimInput(
        previous.statement,
        previous.kind,
        state,
        tuple(
            ClaimCitationInput(
                c.label, c.relation, c.excerpt.field, c.excerpt.start, c.excerpt.end, c.excerpt.text
            )
            for c in previous.citations
        ),
        previous.unresolved_conflicts if conflicts is None else conflicts,
        reason,
    )
    async with container.session_factory() as session:
        return await container.report_claims(session).update(
            actor, previous.claim_id, previous.id, value, CONTEXT
        )

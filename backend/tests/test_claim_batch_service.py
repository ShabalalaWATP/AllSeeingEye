"""Model proposals recheck authority and persist as one bounded transaction."""

from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from ase.application.reports import claims as claims_module
from ase.application.reports.claim_proposals import ClaimProposal
from ase.domain.claim_revisions import ClaimReviewState
from ase.domain.errors import Conflict, InvalidRequest, Unauthenticated
from team_helpers import CONTEXT
from test_claim_origin import origin
from test_claim_repository import seed
from test_report_claim_service import value_for
from test_saved_map_views import claims_for


def proposals_for(version):
    value = value_for(version)
    return tuple(
        ClaimProposal(statement, value.kind, value.citations, ())
        for statement in ("The source reports the observation.", "The source names this event.")
    )


async def test_batch_releases_transaction_and_saves_provenance(client, container, user):
    claims = await claims_for(client, container, user)
    report, version, _ = await seed(container, user)
    provenance = origin(container.clock.now())
    async with container.session_factory() as session:
        service = container.report_claims(session)
        anchor = await service.prepare_proposals(claims, report.id, 1)
        assert not session.in_transaction()
        revisions = await service.persist_proposals(
            claims, anchor, proposals_for(version), provenance, CONTEXT
        )
        assert len(revisions) == 2
        for revision in revisions:
            assert revision.state is ClaimReviewState.PROPOSED
            assert revision.model_origin == provenance
            assert (await service.get(claims, revision.claim_id))[1] == revision
        assert (await service.list(claims, report.id, 1))[1] == 3


@pytest.mark.parametrize(
    "failure",
    ["quota", "stale_session", "evidence", "invalid_last", "mutable_version", "mutable_body"],
)
async def test_rejection_saves_no_part_of_batch(client, container, user, monkeypatch, failure):
    claims = await claims_for(client, container, user)
    report, version, _ = await seed(container, user)
    async with container.session_factory() as session:
        service = container.report_claims(session)
        anchor = await service.prepare_proposals(claims, report.id, 1)
        proposals = proposals_for(version)
        attempt = claims
        expected = InvalidRequest
        if failure == "quota":
            monkeypatch.setattr(claims_module, "MAX_SCOPE_CLAIMS", 2)
        elif failure == "stale_session":
            attempt = replace(claims, security_version=claims.security_version + 1)
            expected = Unauthenticated
        elif failure == "evidence":
            anchor = replace(anchor, evidence_sha256="0" * 64)
            expected = Conflict
        elif failure == "mutable_version":
            anchor.version.number += 1
            expected = Conflict
        elif failure == "mutable_body":
            anchor.version.body = replace(anchor.version.body, key_judgements=())
            expected = Conflict
        else:
            proposals = (proposals[0], replace(proposals[1], statement=""))
        with pytest.raises(expected):
            await service.persist_proposals(
                attempt, anchor, proposals, origin(container.clock.now()), CONTEXT
            )
        await session.rollback()
        assert (await service.list(claims, report.id, 1))[1] == 1


async def test_repository_failure_rolls_back_earlier_claims(client, container, user, monkeypatch):
    claims = await claims_for(client, container, user)
    report, version, _ = await seed(container, user)
    async with container.session_factory() as session:
        service = container.report_claims(session)
        anchor = await service.prepare_proposals(claims, report.id, 1)
        original = service.claims.create
        calls = 0

        async def fail_second(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("simulated storage failure")
            return await original(*args)

        monkeypatch.setattr(service.claims, "create", AsyncMock(side_effect=fail_second))
        with pytest.raises(RuntimeError, match="simulated"):
            await service.persist_proposals(
                claims, anchor, proposals_for(version), origin(container.clock.now()), CONTEXT
            )
        assert not session.in_transaction()
        assert (await service.list(claims, report.id, 1))[1] == 1

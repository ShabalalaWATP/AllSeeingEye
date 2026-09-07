"""Claim service uses current authority and preserves frozen report history."""

from dataclasses import replace
from uuid import uuid4

import pytest

from ase.application.reports import claims as claims_module
from ase.application.reports.claims import ClaimInput
from ase.domain.claim_revisions import (
    ClaimCitationInput,
    ClaimKind,
    ClaimRelation,
    ClaimReviewState,
)
from ase.domain.errors import Conflict, InvalidRequest, NotFound, Unauthenticated
from team_helpers import CONTEXT
from test_claim_repository import seed
from test_saved_map_views import claims_for


def value_for(version):
    item = version.evidence[0]
    return ClaimInput(
        "The source reports the observation.",
        ClaimKind.REPORTED_FACT,
        ClaimReviewState.PROPOSED,
        (
            ClaimCitationInput(
                item.label, ClaimRelation.SUPPORTING, "title", 0, len(item.title), item.title
            ),
        ),
        (),
        "Capture for review.",
    )


async def test_create_revise_and_read_previous_keep_report_unchanged(client, container, user):
    claims = await claims_for(client, container, user)
    report, version, _ = await seed(container, user)
    value = value_for(version)
    async with container.session_factory() as session:
        first = await container.report_claims(session).create(claims, report.id, 1, value, CONTEXT)
    async with container.session_factory() as session:
        service = container.report_claims(session)
        second = await service.update(
            claims,
            first.claim_id,
            first.id,
            replace(value, state=ClaimReviewState.REVIEWED, reason="Reviewed attribution."),
            CONTEXT,
        )
        assert (await service.get(claims, first.claim_id, first.id))[1] == first
        assert (await service.get(claims, first.claim_id))[1] == second
        stored = await container.repositories(session).reports.get_version(report.id, 1)
        assert stored.body == version.body and stored.evidence == version.evidence
    async with container.session_factory() as session:
        with pytest.raises(Conflict):
            await container.report_claims(session).update(
                claims, first.claim_id, first.id, value, CONTEXT
            )


@pytest.mark.parametrize("quota", ["count", "bytes", "revisions"])
async def test_quota_rejection_retains_latest(client, container, user, monkeypatch, quota):
    claims = await claims_for(client, container, user)
    report, version, first = await seed(container, user)
    value = value_for(version)
    async with container.session_factory() as session:
        service = container.report_claims(session)
        if quota == "count":
            monkeypatch.setattr(claims_module, "MAX_SCOPE_CLAIMS", 1)
        elif quota == "bytes":
            monkeypatch.setattr(claims_module, "MAX_SCOPE_BYTES", 1)
        else:
            monkeypatch.setattr(claims_module, "MAX_CLAIM_REVISIONS", 1)
        with pytest.raises(InvalidRequest, match="limit"):
            if quota == "count":
                await service.create(claims, report.id, 1, value, CONTEXT)
            else:
                await service.update(claims, first.claim_id, first.id, value, CONTEXT)
        assert (await service.get(claims, first.claim_id))[1] == first


@pytest.mark.parametrize("operation", ["create", "get", "update"])
async def test_stale_session_cannot_read_or_write_claims(client, container, user, operation):
    claims = await claims_for(client, container, user)
    report, version, first = await seed(container, user)
    stale = replace(claims, security_version=claims.security_version + 1)
    async with container.session_factory() as session:
        service = container.report_claims(session)
        with pytest.raises(Unauthenticated):
            if operation == "get":
                await service.get(stale, first.claim_id)
            elif operation == "create":
                await service.create(stale, report.id, 1, value_for(version), CONTEXT)
            else:
                await service.update(stale, first.claim_id, first.id, value_for(version), CONTEXT)


async def test_foreign_personal_report_is_hidden(client, container, user):
    claims = await claims_for(client, container, user)
    report, version, first = await seed(container, replace(user, id=uuid4()))
    async with container.session_factory() as session:
        with pytest.raises(NotFound):
            await container.report_claims(session).get(claims, first.claim_id)
    async with container.session_factory() as session:
        with pytest.raises(NotFound):
            await container.report_claims(session).create(
                claims, report.id, 1, value_for(version), CONTEXT
            )

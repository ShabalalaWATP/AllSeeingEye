"""Automatic proposals use frozen routing and buffer writes until final authorisation."""

from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from ase.application.model_routing import ModelRouting
from ase.application.reports.automatic_claims import AutomaticClaims
from ase.domain.claim_generation import ClaimGenerationStatus
from ase.domain.llm import LlmResult
from test_claim_revisions import inputs
from test_generate_claims import output_for, setup_model


@pytest.mark.parametrize("mode", ["completed", "invalid", "empty", "rate_limited", "bad_origin"])
async def test_automatic_stage_preserves_exact_revision_and_routing(container, user, mode):
    profile = await setup_model(container, user)
    async with container.session_factory() as session:
        repos = container.repositories(session)
        routing = await ModelRouting(repos.llm_profiles, repos.llm_bindings).snapshot()
        await session.rollback()
        # Changing a repository profile after the snapshot must not redirect this stage.
        await repos.llm_profiles.save(replace(profile, model="new-assignment"))
        await session.commit()
    version, _ = inputs()
    gateway = AsyncMock()
    output = output_for(version)
    if mode == "invalid":
        output = "not JSON"
    elif mode == "empty":
        output = '{"claims":[]}'
    returned = "x" * 2049 if mode == "bad_origin" else "returned-model"
    gateway.complete.return_value = LlmResult(output, returned, 1, 10, 20)
    if mode == "rate_limited":
        for _ in range(6):
            container.limiter.hit(f"claims:user:{user.id}", 6, 3600)
    stage = AutomaticClaims(gateway, container.cipher, container.clock, container.limiter)
    pending = await stage.prepare(version, user.id, routing.profile_for)
    assert pending.report_id == version.report_id and pending.version_id == version.id
    if mode == "completed":
        assert pending.receipt.status is ClaimGenerationStatus.COMPLETED
        assert pending.receipt.revision_ids == tuple(row.id for row in pending.revisions)
        assert pending.receipt.model_origin.requested_model == profile.model
        assert pending.revisions[0].model_origin == pending.receipt.model_origin
    else:
        assert pending.receipt.status.value == ("invalid" if mode == "bad_origin" else mode)
        assert pending.revisions == ()
    if mode == "rate_limited":
        gateway.complete.assert_not_called()
        assert pending.usage is None
    else:
        assert gateway.complete.await_args.args[2] == profile.model
        assert pending.usage.completion_tokens == 20
    async with container.session_factory() as session:
        assert await container.repositories(session).llm_usage.list_recent(10) == []


async def test_unsupported_input_does_not_claim_a_model_attempt(container, user):
    await setup_model(container, user)
    async with container.session_factory() as session:
        r = container.repositories(session)
        routing = await ModelRouting(r.llm_profiles, r.llm_bindings).snapshot()
    version, _ = inputs()
    version.evidence = ()
    gateway = AsyncMock()
    stage = AutomaticClaims(gateway, container.cipher, container.clock, container.limiter)
    result = await stage.prepare(version, user.id, routing.profile_for)
    assert result.receipt.status is ClaimGenerationStatus.UNSUPPORTED
    assert result.receipt.model_origin is None and result.usage is None
    gateway.complete.assert_not_called()


async def test_missing_model_and_unavailable_provider_do_not_invent_returned_model(container, user):
    version, _ = inputs()
    gateway = AsyncMock()
    lookup = AsyncMock(return_value=None)
    stage = AutomaticClaims(gateway, container.cipher, container.clock, container.limiter)
    missing = await stage.prepare(version, user.id, lookup)
    assert missing.receipt.status is ClaimGenerationStatus.NO_MODEL
    assert missing.usage is None and missing.receipt.model_origin is None
    gateway.complete.assert_not_called()
    profile = await setup_model(container, user)
    lookup.return_value = profile
    gateway.complete.side_effect = TimeoutError
    unavailable = await stage.prepare(version, user.id, lookup)
    assert unavailable.receipt.status is ClaimGenerationStatus.UNAVAILABLE
    assert unavailable.receipt.model_origin is None
    assert unavailable.usage.error == "unavailable" and not unavailable.usage.ok

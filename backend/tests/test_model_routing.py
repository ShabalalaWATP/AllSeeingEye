"""Destination scope and frozen configuration determine every text model in a run."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.application.model_routing import ModelRouting
from ase.domain.errors import NoModelAvailable
from ase.domain.llm import LlmProfile, LlmRole
from feeds_helpers import NOW

TEXT_ROLES = frozenset(set(LlmRole) - {LlmRole.EMBEDDINGS})


def profile(name="global", **changes):
    value = LlmProfile(
        uuid4(),
        name,
        "http://localhost:11434/v1",
        name,
        "encrypted-fixture",
        "ture",
        TEXT_ROLES,
        2000,
        0.1,
        True,
        NOW,
        NOW,
    )
    value = replace(value, **changes)
    value.tested_at = NOW
    value.tested_revision = value.revision
    value.tested_config_hash = value.config_hash
    return value


def routing(profiles, assignments):
    repository = AsyncMock()
    repository.list_all.return_value = profiles
    repository.get.side_effect = lambda key: next((p for p in profiles if p.id == key), None)
    bindings = AsyncMock()
    bindings.list_all.side_effect = lambda: [
        SimpleNamespace(team_id=scope, **vars(value)) for scope, value in assignments.items()
    ]
    return ModelRouting(repository, bindings), bindings


def binding(value):
    return SimpleNamespace(
        profile_id=value.id, profile_revision=value.revision, tested_config_hash=value.config_hash
    )


async def test_exact_team_override_global_inheritance_and_personal_scope():
    global_profile, team_profile = profile(), profile("team-a")
    team_a, team_b = uuid4(), uuid4()
    service, bindings = routing(
        [team_profile, global_profile],
        {None: binding(global_profile), team_a: binding(team_profile)},
    )
    for scope, expected in (
        (team_a, team_profile),
        (team_b, global_profile),
        (None, global_profile),
    ):
        snapshot = await service.snapshot(team_id=scope)
        for role in TEXT_ROLES:
            assert snapshot.required(role).id == expected.id
        assert await snapshot.profile_for(LlmRole.EMBEDDINGS) is None
    assert bindings.list_all.await_count == 3


async def test_explicit_profile_cannot_bypass_a_binding():
    configured, other = profile(), profile("other")
    service, _ = routing([other, configured], {None: binding(configured)})
    result = await service.snapshot(profile_id=other.id)
    assert result.required(LlmRole.ASSESSMENT).id == configured.id


@pytest.mark.parametrize("fault", ["missing", "disabled", "missing_role"])
async def test_broken_team_assignment_never_falls_back_to_global(fault):
    configured, global_profile = profile("team"), profile()
    team_id = uuid4()
    if fault == "disabled":
        configured.enabled = False
    if fault == "missing_role":
        configured.roles = frozenset({LlmRole.ASSESSMENT})
    values = [global_profile] + ([] if fault == "missing" else [configured])
    service, _ = routing(values, {team_id: binding(configured), None: binding(global_profile)})
    with pytest.raises(NoModelAvailable):
        await service.snapshot(team_id=team_id)


async def test_legacy_roles_are_selected_only_without_a_binding():
    assessment = profile(roles=frozenset({LlmRole.ASSESSMENT}))
    direction = profile("planner", roles=frozenset({LlmRole.DIRECTION}))
    service, _ = routing([assessment, direction], {})
    result = await service.snapshot(profile_id=assessment.id)
    assert result.required(LlmRole.ASSESSMENT).id == assessment.id
    assert (await result.profile_for(LlmRole.DIRECTION)).id == direction.id
    assert await result.profile_for(LlmRole.DEVIL) is None
    with pytest.raises(NoModelAvailable):
        await service.snapshot(profile_id=uuid4())


async def test_configuration_switch_and_mutation_affect_only_the_next_snapshot():
    first, second = profile("first"), profile("second")
    assignments = {None: binding(first)}
    service, _ = routing([first, second], assignments)
    snapshot = await service.snapshot()
    assignments[None] = binding(second)
    first.model = "later-edit"
    returned = snapshot.required(LlmRole.ASSESSMENT)
    returned.model = "caller-edit"
    assert snapshot.required(LlmRole.ASSESSMENT).model == "first"
    assert (await snapshot.profile_for(LlmRole.DEVIL)).model == "first"
    assert (await service.snapshot()).required(LlmRole.ASSESSMENT).model == "second"


async def test_shared_translation_never_uses_an_unassigned_team_profile():
    team_profile = profile("team")
    service, _ = routing([team_profile], {uuid4(): binding(team_profile)})
    with pytest.raises(NoModelAvailable):
        await service.snapshot(role=LlmRole.TRANSLATION)
    # A global assignment always wins, regardless of repository ordering.
    global_profile = profile("shared")
    service, _ = routing([team_profile, global_profile], {None: binding(global_profile)})
    result = await service.snapshot(role=LlmRole.TRANSLATION)
    assert result.required(LlmRole.TRANSLATION).id == global_profile.id


@pytest.mark.parametrize("fault", ["revision", "hash", "changed_config"])
async def test_saved_binding_must_match_current_successfully_tested_configuration(fault):
    configured = profile()
    assignment = binding(configured)
    if fault == "revision":
        assignment.profile_revision += 1
    elif fault == "hash":
        assignment.tested_config_hash = "wrong"
    else:
        configured.model = "untested-model"
    service, _ = routing([configured], {None: assignment})
    with pytest.raises(NoModelAvailable):
        await service.snapshot()


async def test_no_binding_repository_supports_legacy_and_empty_embeddings():
    service, _ = routing([], {})
    assert await service.embeddings() is None
    with pytest.raises(NoModelAvailable):
        await service.snapshot()
    candidate = profile()
    repository = AsyncMock()
    repository.list_all.return_value = [candidate]
    legacy = ModelRouting(repository)
    snapshot = await legacy.snapshot()
    assert snapshot.required(LlmRole.ASSESSMENT).id == candidate.id
    with pytest.raises(NoModelAvailable):
        snapshot.required(LlmRole.EMBEDDINGS)


async def test_existing_activation_remains_valid_after_failed_retest_clears_latest_proof():
    configured = profile()
    assignment = binding(configured)
    configured.tested_at = None
    configured.tested_revision = None
    configured.tested_config_hash = None
    service, _ = routing([configured], {None: assignment})
    assert (await service.snapshot()).required(LlmRole.ASSESSMENT).id == configured.id

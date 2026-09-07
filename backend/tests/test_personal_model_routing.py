"""Personal routing follows destination ownership and cannot redirect shared processing."""

from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.application.model_routing import ModelRouting
from ase.domain.errors import NoModelAvailable
from ase.domain.llm import LlmConnectionBinding, LlmRole
from ase.domain.model_routing_records import routing_from_dict, routing_to_dict
from feeds_helpers import NOW
from test_model_routing import profile


def configured():
    owner, team = uuid4(), uuid4()
    global_profile, personal_profile, team_profile = [
        profile(name) for name in ("global", "personal", "team")
    ]
    values = [personal_profile, team_profile, global_profile]
    profiles = AsyncMock()
    profiles.list_all.return_value = values
    profiles.get.side_effect = lambda key: next((item for item in values if item.id == key), None)
    bindings = AsyncMock()
    bindings.list_all.return_value = [
        LlmConnectionBinding(
            None, personal_profile.id, 1, personal_profile.config_hash, NOW, owner, user_id=owner
        ),
        LlmConnectionBinding(team, team_profile.id, 1, team_profile.config_hash, NOW, owner),
        LlmConnectionBinding(None, global_profile.id, 1, global_profile.config_hash, NOW, owner),
    ]
    return ModelRouting(profiles, bindings), owner, team, values, bindings


async def test_personal_team_inherited_team_and_shared_roles_have_distinct_audiences():
    routing, owner, team, _, _ = configured()
    for team_id, user_id, expected in [
        (None, owner, "personal"),
        (team, owner, "team"),
        (uuid4(), owner, "global"),
        (None, uuid4(), "global"),
        (None, None, "global"),
    ]:
        result = await routing.snapshot(team_id=team_id, personal_owner_id=user_id)
        assert result.required(LlmRole.ASSESSMENT).model == expected
        assert result.required(LlmRole.TRANSLATION).model == expected
        assert result.provenance.policy == expected
        assert result.provenance.binding_user_id == (owner if expected == "personal" else None)
        encoded = routing_to_dict(result.provenance)
        assert routing_from_dict(encoded) == result.provenance
        if expected != "personal":
            assert "binding_user_id" not in encoded


@pytest.mark.parametrize("fault", ["missing", "disabled", "revision", "hash"])
async def test_invalid_personal_assignment_fails_closed(fault):
    routing, owner, _, values, bindings = configured()
    if fault == "missing":
        values.pop(0)
    elif fault == "disabled":
        values[0].enabled = False
    elif fault == "revision":
        bindings.list_all.return_value[0] = replace(
            bindings.list_all.return_value[0], profile_revision=2
        )
    else:
        bindings.list_all.return_value[0] = replace(
            bindings.list_all.return_value[0], tested_config_hash="0" * 64
        )
    with pytest.raises(NoModelAvailable):
        await routing.snapshot(personal_owner_id=owner)
    assert (await routing.snapshot(team_id=uuid4(), personal_owner_id=owner)).required(
        LlmRole.ASSESSMENT
    ).model == "global"


async def test_personal_profiles_never_enter_shared_embeddings_or_translation():
    routing, _owner, _, values, bindings = configured()
    values[0].roles |= {LlmRole.EMBEDDINGS}
    assert await routing.embeddings() is None
    bindings.list_all.return_value = bindings.list_all.return_value[:1]
    with pytest.raises(NoModelAvailable):
        await routing.snapshot(role=LlmRole.TRANSLATION)
    assert await routing.embeddings() is None


@pytest.mark.parametrize("change", [{"policy": "personal"}, {"binding_user_id": str(uuid4())}])
async def test_codec_rejects_mixed_or_missing_personal_audience(change):
    routing, _, _, _, _ = configured()
    encoded = routing_to_dict((await routing.snapshot()).provenance)
    with pytest.raises(ValueError):
        routing_from_dict({**encoded, **change})

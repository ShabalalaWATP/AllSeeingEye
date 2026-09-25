"""The research readiness flag follows real routing and reveals nothing but a boolean."""

from dataclasses import replace
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.application.research_readiness import ResearchReadiness
from ase.container import Container
from ase.domain.llm import LlmConnectionBinding, LlmProfile, LlmRole
from ase.domain.teams import Team
from ase.domain.users import User
from feeds_helpers import NOW
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_model_routing import profile


class Profiles:
    def __init__(self, items: list[LlmProfile]) -> None:
        self.items = items

    async def get(self, profile_id):
        return next((item for item in self.items if item.id == profile_id), None)

    async def list_all(self):
        return list(self.items)


class Bindings:
    def __init__(self, items: list[LlmConnectionBinding]) -> None:
        self.items = items

    async def list_all(self):
        return list(self.items)


class Teams:
    def __init__(self, teams: list[Team]) -> None:
        self.teams = teams
        self.calls: list[tuple[object, bool]] = []

    async def list_visible(self, user_id, *, administrator):
        self.calls.append((user_id, administrator))
        return list(self.teams)


def bind(value: LlmProfile, team_id=None, user_id=None) -> LlmConnectionBinding:
    return LlmConnectionBinding(
        team_id, value.id, value.revision, value.config_hash, NOW, uuid4(), user_id=user_id
    )


def team(active: bool = True) -> Team:
    return Team(uuid4(), "Analysts", active, uuid4(), NOW, NOW)


def readiness(profiles, bindings, teams=()):
    visible = Teams(list(teams))
    return ResearchReadiness(Profiles(profiles), Bindings(bindings), visible), visible


async def test_not_configured_without_any_connection() -> None:
    user_id = uuid4()
    service, teams = readiness([], [])
    assert await service.available(user_id) is False
    # Team destinations are checked with membership scope, never as an administrator.
    assert teams.calls == [(user_id, False)]


async def test_tested_global_assignment_makes_research_available() -> None:
    configured = profile()
    service, teams = readiness([configured], [bind(configured)])
    assert await service.available(uuid4()) is True
    assert teams.calls == []


@pytest.mark.parametrize("fault", ["disabled", "changed_after_test", "missing", "missing_role"])
async def test_inactive_or_untested_assignment_is_not_ready(fault: str) -> None:
    configured = profile()
    saved = bind(configured)
    if fault == "disabled":
        configured.enabled = False
    elif fault == "changed_after_test":
        configured.model = "edited-without-a-new-test"
    elif fault == "missing_role":
        configured.roles = frozenset({LlmRole.ASSESSMENT})
    profiles = [] if fault == "missing" else [configured]
    service, _ = readiness(profiles, [saved])
    assert await service.available(uuid4()) is False


async def test_team_override_counts_only_for_active_member_teams() -> None:
    configured = profile("team-model")
    member_team, archived = team(), team(active=False)
    bindings = [bind(configured, team_id=member_team.id), bind(configured, team_id=archived.id)]
    service, _ = readiness([configured], bindings, [member_team])
    assert await service.available(uuid4()) is True
    service, _ = readiness([configured], bindings, [archived])
    assert await service.available(uuid4()) is False
    # Another team's override does not help someone outside that team.
    service, _ = readiness([configured], bindings, [])
    assert await service.available(uuid4()) is False


async def test_personal_override_is_ready_for_its_owner_only() -> None:
    configured = profile("personal-model")
    owner = uuid4()
    service, _ = readiness([configured], [bind(configured, user_id=owner)])
    assert await service.available(owner) is True
    assert await service.available(uuid4()) is False


async def test_enabled_role_profiles_without_assignments_remain_usable() -> None:
    legacy = profile("legacy", roles=frozenset({LlmRole.ASSESSMENT}))
    service, _ = readiness([legacy], [])
    assert await service.available(uuid4()) is True
    legacy.enabled = False
    assert await service.available(uuid4()) is False


async def _seed_global(container: Container, admin: User) -> LlmProfile:
    value = replace(
        profile("Private provider label"),
        model="private-model-identifier",
        base_url="https://models.private.example/v1",
    )
    value.api_key_encrypted = container.cipher.encrypt("sk-private-readiness-key")
    value.api_key_hint = "-key"
    value.tested_config_hash = value.config_hash
    async with container.session_factory() as session:
        repos = container.repositories(session)
        await repos.llm_profiles.add(value)
        await repos.llm_bindings.save(replace(bind(value), activated_by=admin.id))
        await session.commit()
    return value


async def test_capabilities_expose_only_the_research_boolean(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    assert (await client.get("/api/capabilities")).status_code == 401
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    before = await client.get("/api/capabilities", headers=headers)
    assert before.json() == {"os_maps": False, "os_layers": [], "ai_research": False}

    value = await _seed_global(container, admin)
    ready = await client.get("/api/capabilities", headers=headers)
    assert ready.json() == {"os_maps": False, "os_layers": [], "ai_research": True}
    for secret in (
        value.name,
        value.model,
        value.base_url,
        "models.private.example",
        "sk-private-readiness-key",
        value.api_key_encrypted,
        str(value.id),
        "openai",
    ):
        assert secret not in ready.text

    async with container.session_factory() as session:
        repos = container.repositories(session)
        stored = await repos.llm_profiles.get(value.id)
        assert stored is not None
        stored.enabled = False
        await repos.llm_profiles.save(stored)
        await session.commit()
    inactive = await client.get("/api/capabilities", headers=headers)
    assert inactive.json()["ai_research"] is False

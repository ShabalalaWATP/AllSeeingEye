"""Admin model probes select embeddings only when that is the profile's sole role."""

from collections.abc import Sequence

from httpx import AsyncClient

from ase.application.admin.llm import TestLlmProfileUseCase as ProbeProfile
from ase.application.dto import RequestContext
from ase.container import Container
from ase.domain.llm import LlmRole
from ase.domain.report_search import EmbeddingResult
from ase.domain.users import User
from helpers import ADMIN_PASSWORD, USER_PASSWORD, bearer, login_token
from report_search_helpers import FakeEmbeddings, add_profile
from test_llm import FakeGateway


async def test_embeddings_only_admin_probe_and_safe_failure(
    client: AsyncClient, container: Container, admin: User, user: User
) -> None:
    embeddings = FakeEmbeddings()
    chat = FakeGateway()
    container.embedding_gateway = embeddings
    container.llm = chat
    async with container.session_factory() as session:
        profile = await add_profile(container, session)
    path = f"/api/admin/llm/profiles/{profile.id}/test"
    assert (
        await client.post(
            path, headers=bearer(await login_token(client, user.email, USER_PASSWORD))
        )
    ).status_code == 403
    headers = bearer(await login_token(client, admin.email, ADMIN_PASSWORD))
    tested = await client.post(path, headers=headers)
    assert tested.status_code == 200 and tested.json()["ok"]
    assert len(embeddings.calls) == 1 and not chat.calls
    assert tested.json()["model"] == profile.model
    assert embeddings.calls[0] == ("Semantic search connection test.",)
    async with container.session_factory() as session:
        usages = await container.repositories(session).llm_usage.list_recent(10)
        assert usages[0].purpose == "embeddings" and usages[0].user_id == admin.id
        assert usages[0].prompt_tokens == 30
    embeddings.fail = True
    failed = await client.post(path, headers=headers)
    assert failed.status_code == 200 and not failed.json()["ok"]
    assert "DO NOT DISPLAY" not in failed.text and "test-key" not in failed.text
    async with container.session_factory() as session:
        usages = await container.repositories(session).llm_usage.list_recent(10)
        assert any(not usage.ok and usage.purpose == "embeddings" for usage in usages)
        assert all("DO NOT DISPLAY" not in str(usage.error) for usage in usages)
        profile.roles = frozenset({LlmRole.EMBEDDINGS, LlmRole.ASSESSMENT})
        await container.repositories(session).llm_profiles.save(profile)
        await session.commit()
    mixed = await client.post(path, headers=headers)
    assert mixed.json()["ok"] and len(chat.calls) == 1 and len(embeddings.calls) == 2


async def test_missing_or_invalid_embedding_probe(container: Container, admin: User) -> None:
    class EmptyEmbeddings:
        async def embed(
            self, base_url: str, api_key: str, model: str, texts: Sequence[str]
        ) -> EmbeddingResult:
            return EmbeddingResult((), 0)

    async with container.session_factory() as session:
        profile = await add_profile(container, session)
        repos = container.repositories(session)
        for gateway in (None, EmptyEmbeddings()):
            probe = ProbeProfile(
                repos.llm_profiles,
                repos.llm_usage,
                container.cipher,
                FakeGateway(),
                container.clock,
                container._auditor(repos),
                repos.uow,
                embeddings=gateway,
            )
            outcome = await probe.execute(admin, profile.id, RequestContext(None, None))
            assert not outcome.ok

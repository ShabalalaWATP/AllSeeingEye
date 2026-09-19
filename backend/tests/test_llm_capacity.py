"""Five configured text models, including drafts, with serialised admission."""

import asyncio
from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from ase.adapters.persistence.session import create_session_factory
from ase.api.schemas_llm import LlmProfileIn
from ase.application.dto import RequestContext
from ase.domain.errors import Forbidden, InvalidRequest
from ase.domain.llm import TEXT_ROLES
from ase.domain.users import Role
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from race_database import race_engine
from test_llm_connections import DRAFT, ROOT, draft


async def test_cap_counts_drafts_excludes_embeddings_and_releases_deleted_slot(client, admin):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    drafts = [await draft(client, headers, f"Model {index}") for index in range(5)]
    blocked = await client.post(
        f"{ROOT}/profiles", headers=headers, json={**DRAFT, "name": "Sixth"}
    )
    assert blocked.status_code == 422 and "five" in blocked.text
    embedding = await client.post(
        f"{ROOT}/profiles",
        headers=headers,
        json={**DRAFT, "name": "Embeddings", "roles": ["embeddings"]},
    )
    assert embedding.status_code == 201, embedding.text
    converted = await client.put(
        f"{ROOT}/profiles/{embedding.json()['id']}",
        headers=headers,
        json={**DRAFT, "name": "Converted"},
    )
    assert converted.status_code == 422
    edited = await client.put(
        f"{ROOT}/profiles/{drafts[0]['id']}",
        headers=headers,
        json={**DRAFT, "name": "Edited draft"},
    )
    assert edited.status_code == 200
    assert (
        await client.delete(f"{ROOT}/profiles/{drafts[-1]['id']}", headers=headers)
    ).status_code == 204
    assert (
        await client.post(f"{ROOT}/profiles", headers=headers, json={**DRAFT, "name": "Sixth"})
    ).status_code == 201


async def test_existing_over_cap_profiles_remain_readable_and_editable(client, container, admin):
    headers = bearer(await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD))
    saved = await draft(client, headers)
    async with container.session_factory() as session:
        profiles = container.repositories(session).llm_profiles
        profile = await profiles.get(UUID(saved["id"]))
        assert profile is not None
        for index in range(6):
            await profiles.add(replace(profile, id=uuid4(), name=f"Legacy {index}"))
        await session.commit()
    listed = await client.get(f"{ROOT}/profiles", headers=headers)
    assert listed.status_code == 200 and len(listed.json()["items"]) == 7
    updated = await client.put(
        f"{ROOT}/profiles/{saved['id']}", headers=headers, json={**DRAFT, "name": "Edited"}
    )
    assert updated.status_code == 200
    assert (
        await client.post(f"{ROOT}/profiles", headers=headers, json={**DRAFT, "name": "Eighth"})
    ).status_code == 422


async def test_simultaneous_creates_cannot_overfill_fifth_slot(tmp_path, container, admin):
    engine = await race_engine(tmp_path, "model-cap.db")
    factory = create_session_factory(engine)
    context = RequestContext(None, None)
    async with factory() as session:
        await container.repositories(session).users.add(admin)
        await session.commit()
        for index in range(4):
            await container.create_llm_profile(session).execute(
                admin,
                LlmProfileIn.model_validate({**DRAFT, "name": f"Seed {index}"}).to_input(),
                context,
            )
    entered, release = asyncio.Event(), asyncio.Event()

    async def hold_fifth():
        entered.set()
        await release.wait()

    async def create(name, before_save=None):
        async with factory() as session:
            try:
                await container.create_llm_profile(session).execute(
                    admin,
                    LlmProfileIn.model_validate({**DRAFT, "name": name}).to_input(),
                    context,
                    before_save=before_save,
                )
                return True
            except InvalidRequest:
                await session.rollback()
                return False

    try:
        fifth = asyncio.create_task(create("Fifth", hold_fifth))
        await asyncio.wait_for(entered.wait(), 5)
        sixth = asyncio.create_task(create("Sixth"))
        # The contender must wait on the same guard before counting current profiles.
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(asyncio.shield(sixth), 0.05)
        release.set()
        assert await asyncio.gather(fifth, sixth) == [True, False]
        async with factory() as session:
            profiles = await container.repositories(session).llm_profiles.list_all()
            assert sum(bool(profile.roles & TEXT_ROLES) for profile in profiles) == 5
    finally:
        release.set()
        await engine.dispose()


async def test_waiting_create_rechecks_admin_after_guard_acquisition(tmp_path, container, admin):
    engine = await race_engine(tmp_path, "model-cap-actor.db")
    factory = create_session_factory(engine)
    async with factory() as session:
        await container.repositories(session).users.add(admin)
        await session.commit()

    async def create():
        async with factory() as session:
            await container.create_llm_profile(session).execute(
                admin, LlmProfileIn.model_validate(DRAFT).to_input(), RequestContext(None, None)
            )

    try:
        async with factory() as holder:
            users = container.repositories(holder).users
            await users.lock_administration()
            pending = asyncio.create_task(create())
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(pending), 0.05)
            await users.save(replace(admin, role=Role.USER))
            await holder.commit()
        with pytest.raises(Forbidden):
            await pending
        async with factory() as session:
            assert await container.repositories(session).llm_profiles.list_all() == []
    finally:
        await engine.dispose()

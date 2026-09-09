"""Shared screening resolves only the global model and invalidates changed generations."""

from dataclasses import replace

from ase.container.conflict_screening import GlobalScreeningRuntime
from ase.domain.llm import LlmConnectionBinding
from test_model_routing import profile


async def add_profile(container, value):
    async with container.session_factory() as session:
        await container.repositories(session).llm_profiles.add(value)
        await session.commit()


async def bind(container, admin, value, *, user_id=None):
    async with container.session_factory() as session:
        await container.repositories(session).llm_bindings.save(
            LlmConnectionBinding(
                None,
                value.id,
                value.revision,
                value.config_hash,
                container.clock.now(),
                admin.id,
                user_id=user_id,
            )
        )
        await session.commit()


async def test_real_global_runtime_has_no_private_fallback_and_rejects_changed_binding(
    container, admin, user
):
    runtime = GlobalScreeningRuntime(container)
    assert await runtime.resolve() is None
    private, global_model = profile("private"), profile("global")
    for value in (private, global_model):
        await add_profile(container, value)
    await bind(container, admin, private, user_id=user.id)
    assert await runtime.resolve() is None
    await bind(container, admin, global_model)
    first = await runtime.resolve()
    assert first.profile.id == global_model.id
    async with runtime.release(first) as current:
        assert current
        # Exercises the same nested source-control read as final publication.
        await container.source_admission.enabled_many(("gdelt_events",))
    await bind(container, admin, private)
    async with runtime.release(first) as current:
        assert not current
    assert (await runtime.resolve()).profile.id == private.id


async def test_legacy_selection_and_disabled_or_edited_profile_are_not_released(container):
    value = profile()
    await add_profile(container, value)
    runtime = GlobalScreeningRuntime(container)
    original = await runtime.resolve()
    assert original.profile.id == value.id
    async with container.session_factory() as session:
        await container.repositories(session).llm_profiles.save(replace(value, model="changed"))
        await session.commit()
    async with runtime.release(original) as current:
        assert not current
    async with container.session_factory() as session:
        await container.repositories(session).llm_profiles.save(replace(value, enabled=False))
        await session.commit()
    assert await runtime.resolve() is None

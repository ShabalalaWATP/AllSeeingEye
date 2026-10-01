"""Container shutdown retains interrupted evaluations before closing their dependencies."""

import asyncio

import pytest

from ase.domain.evaluations import EvaluationRunStatus, EvaluationStopReason
from evaluation_run_helpers import ScriptedRunGateway, evaluation_profile, start_run


@pytest.mark.parametrize("close_failure", [False, True])
async def test_disposal_saves_interruption_before_clients_and_database_close(
    container, admin, monkeypatch, close_failure
):
    calling = asyncio.Event()

    async def wait_for_shutdown(_count):
        calling.set()
        await asyncio.Event().wait()

    profile = await evaluation_profile(container)
    container.llm = ScriptedRunGateway(hook=wait_for_shutdown)
    run = await start_run(container, admin, profile)
    await asyncio.wait_for(calling.wait(), timeout=30)
    closed = []
    close_http = container.http.aclose
    engine_type = type(container.engine)
    close_database = engine_type.dispose

    async def verify_saved_interruption():
        async with container.session_factory() as session:
            stored = await container.evaluation_run_repository(session).get(run.id)
        assert stored is not None
        assert stored.status is EvaluationRunStatus.STOPPED
        assert stored.stop_reason is EvaluationStopReason.INTERRUPTED
        assert stored.has_artefact

    async def checked_http_close():
        await verify_saved_interruption()
        await close_http()
        closed.append("http")
        if close_failure:
            raise RuntimeError("HTTP close failed")

    async def checked_database_close(engine, close=True):
        assert engine is container.engine
        await verify_saved_interruption()
        await close_database(engine, close=close)
        closed.append("database")

    # Restore the callbacks before the fixture performs its own final disposal.
    with monkeypatch.context() as patch:
        patch.setattr(container.http, "aclose", checked_http_close)
        patch.setattr(engine_type, "dispose", checked_database_close)
        if close_failure:
            with pytest.raises(RuntimeError, match="HTTP close failed"):
                await container.dispose()
        else:
            await container.dispose()
    assert closed == ["http", "database"]

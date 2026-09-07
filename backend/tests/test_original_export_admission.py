"""Admission covers original blob reads and errors release capacity before handoff."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from ase.application.reports.evidence_package import _PACKAGE_SLOTS
from ase.application.reports.export_claim_package import ExportClaimPackage
from ase.domain.errors import NotFound, RateLimited


def available_slots():
    acquired = 0
    try:
        while acquired < 2 and _PACKAGE_SLOTS.acquire(blocking=False):
            acquired += 1
        return acquired
    finally:
        for _ in range(acquired):
            _PACKAGE_SLOTS.release()


def exporter():
    selected = SimpleNamespace(
        record=object(), version=object(), revisions=(), identity_revisions=()
    )
    selector = SimpleNamespace(resolve=AsyncMock(return_value=selected), recheck=AsyncMock())
    originals = SimpleNamespace(select=AsyncMock(return_value=(object(),)), recheck=AsyncMock())
    renderer = SimpleNamespace(render=Mock(return_value=b"zip"))
    return ExportClaimPackage(selector, renderer, originals), selector, originals, renderer


async def test_busy_export_rejects_before_loading_original_bytes():
    usecase, selector, originals, renderer = exporter()
    assert _PACKAGE_SLOTS.acquire(blocking=False)
    assert _PACKAGE_SLOTS.acquire(blocking=False)
    try:
        with pytest.raises(RateLimited):
            await usecase.execute(object(), uuid4(), 1, (), asset_ids=(uuid4(),))
        originals.select.assert_not_awaited()
        selector.resolve.assert_not_awaited()
        renderer.render.assert_not_called()
    finally:
        _PACKAGE_SLOTS.release()
        _PACKAGE_SLOTS.release()


@pytest.mark.parametrize("failure", [NotFound(), asyncio.CancelledError()])
@pytest.mark.parametrize("stage", ["originals", "annotations"])
async def test_pre_worker_error_or_cancellation_releases_admission(stage, failure):
    usecase, selector, originals, renderer = exporter()
    operation = originals.select if stage == "originals" else selector.resolve
    operation.side_effect = failure
    with pytest.raises(type(failure)):
        await usecase.execute(object(), uuid4(), 1, (), asset_ids=(uuid4(),))
    assert available_slots() == 2
    renderer.render.assert_not_called()


async def test_original_revocation_after_render_prevents_download():
    usecase, selector, originals, renderer = exporter()
    originals.recheck.side_effect = NotFound()
    with pytest.raises(NotFound):
        await usecase.execute(object(), uuid4(), 1, (), asset_ids=(uuid4(),))
    renderer.render.assert_called_once()
    selector.recheck.assert_awaited_once()
    originals.recheck.assert_awaited_once()
    assert available_slots() == 2


@pytest.mark.parametrize("stage", ["annotations", "originals"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_admission_retained_while_final_recheck_waits(stage, cancel):
    usecase, selector, originals, renderer = exporter()
    entered, finish = asyncio.Event(), asyncio.Event()

    async def blocked(*args):
        entered.set()
        await finish.wait()

    operation = originals.recheck if stage == "originals" else selector.recheck
    operation.side_effect = blocked
    assert _PACKAGE_SLOTS.acquire(blocking=False)
    task = asyncio.create_task(usecase.execute(object(), uuid4(), 1, (), asset_ids=(uuid4(),)))
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        renderer.render.assert_called_once()
        other, _, other_originals, _ = exporter()
        with pytest.raises(RateLimited):
            await other.execute(object(), uuid4(), 1, (), asset_ids=(uuid4(),))
        other_originals.select.assert_not_awaited()
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            finish.set()
            assert (await task).content == b"zip"
        assert available_slots() == 1
    finally:
        finish.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        _PACKAGE_SLOTS.release()
    assert available_slots() == 2

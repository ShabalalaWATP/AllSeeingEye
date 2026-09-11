"""Native web provider usage survives cancelled report work without duplicate final accounting."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace

import pytest

from ase.adapters.persistence.web_search_usage import SqlWebSearchUsage
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.production_types import Totals
from helpers import FakeClock
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE
from test_fresh_web_research import setup
from web_search_helpers import NOW, QUERY, Admission, Cipher, Gateway, job


async def test_durable_cancellation_usage_does_not_depend_on_report_save(container, user):
    selected = await seed_legacy_profile(
        container,
        {
            **PROFILE,
            "base_url": "https://api.openai.com/v1",
            "roles": ["direction"],
        },
    )

    async def lookup(_):
        return selected

    gateway = Gateway()
    gateway.hold = True
    service = FreshWebResearch(
        gateway,
        Admission(),
        FakeClock(NOW),
        container.limiter,
        SqlWebSearchUsage(container.session_factory).record,
    )
    totals = Totals()
    task = asyncio.create_task(
        service.collect(replace(job(), actor=user), QUERY, totals, container.cipher, lookup)
    )
    await gateway.started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with container.session_factory() as session:
        usage = await container.repositories(session).llm_usage.list_recent(20)
    assert len(usage) == 1 and usage[0].profile_id == selected.id
    assert usage[0].user_id == user.id and usage[0].ok is False
    assert usage[0].prompt_tokens is None and "cancelled" in usage[0].error
    assert totals.usage == [] and gateway.cancelled


async def test_success_counts_tokens_once_and_removes_only_durably_saved_usage():
    service, _, _, lookup, _ = setup()
    saved = []

    async def sink(usage):
        saved.append(usage)

    service._usage_sink = sink
    totals = Totals()
    result = await service.collect(job(), QUERY, totals, Cipher(), lookup)
    assert result.status == "completed" and len(saved) == 1
    assert totals.usage == [] and totals.prompt_tokens == 30 and totals.completion_tokens == 15


async def test_failed_usage_sink_does_not_duplicate_uncertain_write_or_mask_cancellation():
    service, _, _, lookup, _ = setup()

    async def broken(_):
        raise RuntimeError("Synthetic database unavailable")

    service._usage_sink = broken
    totals = Totals()
    result = await service.collect(job(), QUERY, totals, Cipher(), lookup)
    assert result.status == "completed" and totals.usage == []
    assert any(finding.rule == "fresh_web_usage" for finding in totals.findings)
    gateway = Gateway()
    gateway.hold = True
    service._gateway = gateway
    totals = Totals()
    task = asyncio.create_task(service.collect(job(), QUERY, totals, Cipher(), lookup))
    await gateway.started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert totals.usage == []
    assert any(finding.rule == "fresh_web_usage" for finding in totals.findings)


async def test_commit_then_close_error_is_not_inserted_again_in_report_totals():
    service, _, _, lookup, _ = setup()
    committed = []

    async def commit_then_raise(usage):
        committed.append(usage)
        raise RuntimeError("Synthetic close failure after commit")

    service._usage_sink = commit_then_raise
    totals = Totals()
    result = await service.collect(job(), QUERY, totals, Cipher(), lookup)
    assert result.status == "completed" and len(committed) == 1
    assert totals.usage == [] and totals.prompt_tokens == 30
    assert "could not be confirmed" in totals.findings[0].message


async def test_report_cancellation_during_bookkeeping_allows_short_write_to_finish():
    service, _, _, lookup, _ = setup()
    started, release = asyncio.Event(), asyncio.Event()
    committed = []

    async def sink(usage):
        started.set()
        await release.wait()
        committed.append(usage)

    service._usage_sink = sink
    totals = Totals()
    task = asyncio.create_task(service.collect(job(), QUERY, totals, Cipher(), lookup))
    await started.wait()
    task.cancel()
    await asyncio.sleep(0)
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(committed) == 1 and committed[0].prompt_tokens == 30
    assert totals.usage == []


async def test_cancel_during_final_source_admission_accounts_known_usage_without_release():
    started = asyncio.Event()

    class BlockedAdmission(Admission):
        @asynccontextmanager
        async def guard(self):
            started.set()
            await asyncio.Event().wait()
            yield

    service, _, _, lookup, _ = setup(admission=BlockedAdmission())
    saved = []

    async def sink(usage):
        saved.append(usage)

    service._usage_sink = sink
    totals = Totals()
    task = asyncio.create_task(service.collect(job(), QUERY, totals, Cipher(), lookup))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(saved) == 1 and saved[0].prompt_tokens == 30 and saved[0].completion_tokens == 15
    assert saved[0].ok is False and "before result release" in saved[0].error
    assert totals.usage == []

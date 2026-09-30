"""Wait for committed job progress without mistaking lease heartbeats for work."""

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from sqlalchemy import select

from ase.adapters.persistence.report_job_models import ReportJobRow


async def wait_for_progress(
    tasks: Mapping[Any, asyncio.Task[None]],
    snapshot: Callable[[], Awaitable[Mapping[Any, object]]],
    *,
    idle_timeout: float = 30,
    overall_timeout: float = 600,
    poll_interval: float = 0.25,
) -> None:
    """Give each job its own idle budget and always cancel/join unfinished tasks."""
    loop = asyncio.get_running_loop()
    pending = set(tasks.values())
    try:
        async with asyncio.timeout(overall_timeout):
            previous = await snapshot()
            changed = dict.fromkeys(tasks, loop.time())
            while pending:
                done, pending = await asyncio.wait(pending, timeout=poll_interval)
                for task in done:
                    task.result()
                if not pending:
                    return
                current = await snapshot()
                now = loop.time()
                for key, task in tasks.items():
                    if task not in pending:
                        continue
                    if current.get(key) != previous.get(key):
                        changed[key] = now
                    elif now - changed[key] >= idle_timeout:
                        raise TimeoutError("Report job made no committed checkpoint progress")
                previous = current
    finally:
        for task in tasks.values():
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks.values(), return_exceptions=True)


async def job_progress(container, job_ids):
    # Read small stored fields, avoiding expensive reconstruction/validation of the
    # frozen evidence. Heartbeats change revision/lease but do not change this hash.
    async with container.session_factory() as session:
        rows = await session.execute(
            select(
                ReportJobRow.id,
                ReportJobRow.status,
                ReportJobRow.stage,
                ReportJobRow.payload_sha256,
            ).where(ReportJobRow.id.in_(job_ids))
        )
        return {row.id: (row.status, row.stage, row.payload_sha256) for row in rows}

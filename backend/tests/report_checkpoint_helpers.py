"""Real isolated SQLite checkpoints with observable current-access gates."""

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from ase.adapters.persistence.llm import SqlLlmUsageRepository
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.container.report_job_checkpoints import ReportJobCheckpoints
from report_job_helpers import NOW, job, saved


def reservation(**changes):
    return {
        "id": str(uuid4()),
        "profile_id": str(uuid4()),
        "status": "in_flight",
        "request_hash": "b" * 64,
        "schema": "topic",
        "model": "configured-model",
        "reserved_output": 32000,
        "prompt_tokens": None,
        "completion_tokens": None,
        "latency_ms": 0.0,
        "error": None,
    } | changes


def payload(**changes):
    return {
        "schema_version": 1,
        "input": {
            "template_id": "intsum",
            "routing": {
                "profiles": [
                    {"role": "assessment", "model": "configured-model", "reasoning_effort": "max"}
                ]
            },
        },
        "calls": [],
    } | changes


class CheckpointContainer:
    def __init__(self, factory):
        self.session_factory = factory
        self.now = NOW
        self.clock = SimpleNamespace(now=lambda: self.now)
        self.lock = asyncio.Lock()
        self.source_admission = SimpleNamespace(guard=self.guard)
        self.steps = []
        self.gate_hook = None

    @asynccontextmanager
    async def guard(self):
        async with self.lock:
            yield

    def access_policy(self, session):
        async def background(owner, team, *, for_update):
            assert self.lock.locked() and for_update
            self.steps.append("access")

        return SimpleNamespace(background=background)

    async def report_job_gate(self, session, stored):
        assert self.lock.locked()
        self.steps.append("gate")
        if self.gate_hook:
            await self.gate_hook(session, stored)

    def repositories(self, session):
        return SimpleNamespace(llm_usage=SqlLlmUsageRepository(session))


async def checkpoint_setup(job_storage, **changes):
    _, factory = job_storage
    stored = await saved(
        factory,
        job(
            status="running",
            lease_token=uuid4(),
            lease_until=NOW + timedelta(seconds=45),
            payload=payload(**changes),
        ),
    )
    host = CheckpointContainer(factory)
    return host, stored, ReportJobCheckpoints(host, stored.id, stored.lease_token)


async def current(host, identity):
    async with host.session_factory() as session:
        return await SqlReportJobRepository(session).get(identity)


async def usage(host):
    async with host.session_factory() as session:
        return await SqlLlmUsageRepository(session).list_recent(100)

"""KAN-31/33/34 offline, repeatable before/after probes.

--checkout selects source and tests from an isolated revision. --briefing runs
the real 14-day economy briefing integration fixture with network-free providers.
--profile reports operation counts separately; profiled timings are not comparable
with ordinary runs. The heartbeat microprobe uses a 1.8 MiB synthetic audit field
and a stubbed authority service, so it isolates persistence/parsing cost only.
"""

# ruff: noqa: E402, PLC0415, T201
import argparse
import asyncio
import cProfile
import json
import os
import pstats
import sys
import tempfile
import time
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkout", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument("--briefing", action="store_true")
parser.add_argument("--profile", action="store_true")
parser.add_argument("--rounds", type=int, default=10)
args = parser.parse_args()
if not 1 <= args.rounds <= 100:
    parser.error("rounds must be 1..100")
root = args.checkout.resolve()
sys.path[:0] = [str(root / "backend/src"), str(root / "backend/tests")]
for name in tuple(os.environ):
    if name in {"ASE_TEST_DATABASE_URL", "ASE_TOKEN_RACE_TEST_URL"} or (
        name.startswith("ASE_") and name.endswith("_POSTGRES_URL")
    ):
        os.environ.pop(name)


from ase.adapters.geo.infrastructure import public_infrastructure
from ase.adapters.persistence.monthly_report_usage import reserve_new_call
from ase.adapters.persistence.session import create_engine, create_session_factory
from ase.adapters.store.memory import InMemoryEventStore
from ase.api.schemas_infrastructure import InfrastructureOut
from ase.application.report_jobs.snapshots import freeze_job
from ase.container import Container  # noqa: F401 (register all persistence models)
from ase.container.report_job_checkpoints import ReportJobCheckpoints
from ase.domain.subscription_monthly_budget import MonthlyBudgetPolicy
from helpers import FakeClock
from pytest_support import create_schema, skip_sqlite_fsync
from report_job_helpers import NOW, job, saved
from report_job_snapshot_helpers import fixture_job, fixture_routing


async def microprobes():
    class Guard:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *ignored):
            return None

    async def measure(action, rounds=args.rounds):
        start = time.perf_counter()
        for _ in range(rounds):
            await action()
        return round((time.perf_counter() - start) * 1000 / rounds, 3)

    with tempfile.TemporaryDirectory(prefix="ase-kan28-benchmark-") as directory:
        engine = create_engine(f"sqlite+aiosqlite:///{Path(directory) / 'probe.db'}")
        try:
            skip_sqlite_fsync(engine)
            await create_schema(engine, fresh=True)
            factory = create_session_factory(engine)
            token = uuid4()
            admitted_input = fixture_job()
            frozen = freeze_job(
                admitted_input, fixture_routing(admitted_input), {}, InMemoryEventStore
            )
            stored = await saved(
                factory,
                job(
                    status="running",
                    lease_token=token,
                    lease_until=NOW + timedelta(seconds=40),
                    payload={
                        "schema_version": 1,
                        "summary": {},
                        "input": frozen,
                        "padding": "x" * int(1.8 * 1024 * 1024),
                    },
                ),
            )
            host = SimpleNamespace(
                clock=FakeClock(NOW),
                session_factory=factory,
                source_admission=SimpleNamespace(guard=Guard),
                access_policy=lambda session: SimpleNamespace(background=AsyncMock()),
                report_job_gate=AsyncMock(),
                repositories=lambda session: SimpleNamespace(
                    llm_usage=SimpleNamespace(add=AsyncMock())
                ),
            )
            checkpoints = ReportJobCheckpoints(host, stored.id, token)

            async def heartbeat():
                if hasattr(checkpoints, "renew_lease"):
                    await checkpoints.renew_lease()
                else:
                    await checkpoints.mutate(lambda payload: None)

            result = {"rounds": args.rounds, "heartbeat_cold_ms": await measure(heartbeat, 1)}
            result["heartbeat_warm_ms"] = await measure(heartbeat)
            owner = uuid4()
            for _ in range(50):
                await saved(
                    factory,
                    job(
                        owner_id=owner,
                        payload={
                            "schema_version": 1,
                            "padding": "x" * (150 * 1024),
                            "calls": [
                                {
                                    "status": "uncertain",
                                    "reserved_output": 100,
                                    "dispatched_at": NOW.isoformat(),
                                }
                            ],
                        },
                    ),
                )
            admitted = job(owner_id=owner)

            async def reserve():
                payload = deepcopy(admitted.payload)
                payload["calls"] = [{"status": "in_flight", "reserved_output": 100}]
                async with factory() as session:
                    await reserve_new_call(session, admitted, payload, NOW, MonthlyBudgetPolicy())

            result["reserve_with_50x150KiB_jobs_ms"] = await measure(reserve)
        finally:
            await engine.dispose()
    snapshot = public_infrastructure()
    try:
        from ase.api.catalogue_responses import CatalogueResponses
    except ImportError:
        cache = None
    else:
        cache = CatalogueResponses()

    async def catalogue():
        if cache is None:
            return InfrastructureOut.model_validate(snapshot).model_dump_json().encode()
        return cache.get(
            "/api/map-infrastructure", snapshot, lambda: InfrastructureOut.model_validate(snapshot)
        ).body

    body = await catalogue()
    result["catalogue_bytes"] = len(body)
    result["catalogue_warm_loop_work_ms"] = await measure(catalogue)
    print(json.dumps(result))


profile = cProfile.Profile() if args.profile else None
if profile:
    profile.enable()
start = time.perf_counter()
if args.briefing:
    import pytest

    os.chdir(root / "backend")
    status = pytest.main(
        [
            (
                "tests/test_economy_briefing_api.py::"
                "test_economic_briefing_freezes_dated_context_and_collects_financial_news_in_period[14]"
            ),
            "--no-cov",
            "-q",
        ]
    )
else:
    asyncio.run(microprobes())
    status = 0
print(
    json.dumps(
        {
            "fixture": "14_day_briefing" if args.briefing else "microprobes",
            "profiled": args.profile,
            "wall_seconds": round(time.perf_counter() - start, 3),
        }
    )
)
if profile:
    profile.disable()
    wanted = {
        "restore_job",
        "check_job",
        "check_sources",
        "collection_from_dict",
        "canonical_job_payload",
        "_check_json_tree",
        "from_row",
    }
    counts = {}
    for (filename, _line, name), data in pstats.Stats(profile).stats.items():
        if name in wanted and "ase" in filename:
            counts[f"{Path(filename).name}:{name}"] = {
                "calls": data[1],
                "cpu_seconds": round(data[2], 3),
            }
    print(json.dumps({"operation_counts": counts}))
raise SystemExit(status)

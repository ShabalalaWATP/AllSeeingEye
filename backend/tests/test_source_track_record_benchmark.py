"""Benchmark: a track record over 1,000 visible reports, one selected version each.

The target is sub-second on SQLite. The assertion is a loose regression ceiling because
CI and development machines share CPU; the measured timings are printed for the record.
Run: uv run pytest tests/test_source_track_record_benchmark.py --no-cov -s
"""

import statistics
import sys
import time
from datetime import timedelta

import pytest

from ase.container.source_track_record import source_track_record
from helpers import USER_PASSWORD, bearer, login_token
from track_record_helpers import SOURCE, insert_reports

pytestmark = pytest.mark.slow
REGRESSION_CEILING_SECONDS = 5.0


async def test_thousand_visible_reports_benchmark(client, container, user, capsys):
    start = container.clock.now() - timedelta(days=60)
    # Twelve frozen items per version: one from the source and eleven from others.
    await insert_reports(container, user.id, 1_000, start=start, others=11)
    service_runs = []
    for _ in range(5):
        async with container.session_factory() as session:
            began = time.perf_counter()
            record = await source_track_record(container, session).read(user, SOURCE)
            service_runs.append(time.perf_counter() - began)
    assert (record.reports_considered, record.reports_citing) == (1_000, 1_000)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    http_runs = []
    for _ in range(3):
        began = time.perf_counter()
        response = await client.get(f"/api/sources/{SOURCE}/track-record", headers=headers)
        http_runs.append(time.perf_counter() - began)
        assert response.status_code == 200
    with capsys.disabled():
        sys.stdout.write(
            "\ntrack-record benchmark (1,000 reports, 12 items each): "
            f"service median {statistics.median(service_runs) * 1000:.0f} ms, "
            f"min {min(service_runs) * 1000:.0f} ms; "
            f"HTTP median {statistics.median(http_runs) * 1000:.0f} ms\n"
        )
    assert statistics.median(service_runs) < REGRESSION_CEILING_SECONDS

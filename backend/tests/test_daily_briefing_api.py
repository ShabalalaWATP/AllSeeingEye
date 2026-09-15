"""Daily monitor admission uses the existing report gates and never runs the model inline."""

from datetime import timedelta
from unittest.mock import AsyncMock

from ase.domain.research import ResearchBatch
from feeds_helpers import make_event
from report_job_api_helpers import job_settings, prepared, stored, work

__all__ = ["job_settings"]


async def test_admission_is_authenticated_post_and_idempotent(client, user, container):
    gateway, headers = await prepared(container, client)
    denied = await client.post("/api/live-monitor/briefing")
    assert denied.status_code == 401
    read = await client.get("/api/live-monitor/briefing", headers=headers)
    assert read.status_code == 405
    first = await client.post("/api/live-monitor/briefing", headers=headers)
    assert first.status_code == 202, first.text
    assert first.headers["cache-control"] == "private, no-store"
    payload = first.json()
    assert payload["next_refresh_at"] and "Coverage varies" in payload["coverage_note"]
    assert payload["job"]["status"] == "queued"
    again = await client.post("/api/live-monitor/briefing", headers=headers)
    assert again.status_code == 202 and again.json()["job"]["id"] == payload["job"]["id"]
    assert not gateway.calls


async def test_daily_worker_produces_existing_cited_report_product(
    client, user, container, monkeypatch
):
    gateway, headers = await prepared(container, client)
    observed = container.clock.now() - timedelta(minutes=1)
    collection = AsyncMock(
        return_value=ResearchBatch(
            items=(
                make_event(
                    "daily-observation",
                    source_id="usgs_earthquakes",
                    title="Earthquake instrument observation",
                    published_at=observed,
                    observed_at=observed,
                ),
            )
        )
    )
    monkeypatch.setattr(container.research, "collect", collection)
    # Durable research jobs acquire sources through the checkpointed path.
    monkeypatch.setattr(container.research, "collect_checkpointed", collection)
    admitted = await client.post("/api/live-monitor/briefing", headers=headers)
    assert admitted.status_code == 202, admitted.text
    job_id = admitted.json()["job"]["id"]
    await work(container)
    current = await stored(container, job_id)
    assert current.status in {"completed", "needs_review"}, (current.status, current.error)
    async with container.session_factory() as session:
        record = await container.repositories(session).reports.get(current.report_id)
        version = await container.repositories(session).reports.get_version(record.id, 1)
    assert record.created_by == user.id and version.body.cited_labels()
    assert version.body.cited_labels() <= {item.label for item in version.evidence}
    assert gateway.calls and collection.await_count == 1

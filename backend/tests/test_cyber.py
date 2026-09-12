"""Bounded cyber publication counts preserve uncertainty, time and source admission."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.cisa_kev import SPEC as KEV
from ase.adapters.feeds.cyber import IODA, RANSOMWARE
from ase.adapters.feeds.rss_seeds_cyber import CYBER_SEEDS
from ase.adapters.store.memory import InMemoryEventStore
from ase.application import cyber as cyber_application
from ase.application.cyber import CyberService
from ase.application.feeds.health import HealthRegistry
from ase.domain.cyber import CyberKind, CyberWindowDays, cyber_kind, cyber_window
from ase.domain.cyber_actors import CyberActorReference
from ase.domain.errors import RateLimited
from ase.domain.events import Category, freeze_attributes
from feeds_helpers import NOW, FakeClock, make_event

ACTOR = CyberActorReference(
    "G0001",
    "APT28",
    ("Fancy Bear",),
    "Reference only",
    "https://attack.mitre.org/groups/G0001/",
    NOW,
    (),
)


def observation(key="one", **changes):
    return replace(
        make_event(
            key,
            source_id="cisa_kev",
            category=Category.CYBER,
            subtype="known_exploited_vulnerability",
            title=f"Vulnerability {key}",
            published_at=NOW - timedelta(minutes=1),
            point=None,
        ),
        **changes,
    )


def service(events=(), disabled=()):
    store = InMemoryEventStore()
    store.upsert(events)
    admission = SimpleNamespace(
        enabled_many=AsyncMock(side_effect=lambda ids: {key: key not in disabled for key in ids})
    )
    specs = (KEV, IODA, RANSOMWARE, *(seed.spec for seed in CYBER_SEEDS))
    svc = CyberService(
        store,
        FakeClock(NOW),
        {spec.id: spec for spec in specs},
        admission,
        HealthRegistry(),
        (ACTOR,),
    )
    return svc, admission


async def snapshot(svc, days=CyberWindowDays.TWO):
    return await svc.release(await svc.read(days))


@pytest.mark.parametrize("days", CyberWindowDays)
async def test_publication_range_is_half_open_with_actual_retrieval_dates(days):
    boundary = NOW - timedelta(days=days)
    rows = (
        observation("start", published_at=boundary),
        observation("older", published_at=boundary - timedelta(microseconds=1)),
        observation("last", published_at=NOW - timedelta(microseconds=1)),
        observation("end", published_at=NOW),
        observation("future", published_at=NOW + timedelta(days=1)),
        observation("undated", published_at=None),
        observation("wrong-topic", category=Category.NEWS),
        observation("unreviewed", source_id="unreviewed-cyber"),
    )
    svc, _ = service(rows)
    result = await snapshot(svc, days)
    assert {row.id for row in result.items} == {rows[0].id, rows[2].id}
    assert result.period_from == boundary and result.period_to == result.as_of == NOW
    assert result.window_days == days and result.retained_count == 2
    assert result.items[-1].observed_at == rows[0].observed_at
    assert sum(day.total for day in result.timeline) == 2
    assert "not absence of activity" in result.coverage_note


async def test_all_counts_cover_full_retained_pool_beyond_returned_items():
    rows = tuple(observation(str(index)) for index in range(301))
    svc, _ = service(rows)
    result = await snapshot(svc)
    assert result.retained_count == 301 and result.returned_count == len(result.items) == 200
    assert result.truncated
    assert (
        sum(row.count for row in result.counts) == sum(row.total for row in result.timeline) == 301
    )
    assert next(row for row in result.sources if row.source_id == "cisa_kev").retained_count == 301


async def test_disable_between_read_and_release_removes_rows_counts_and_mentions():
    row = observation(title="APT28 vulnerability report", country_iso="GB")
    svc, admission = service((row,))
    selected = await svc.read()
    admission.enabled_many.side_effect = lambda ids: {key: key != "cisa_kev" for key in ids}
    result = await svc.release(selected)
    assert not result.items and result.retained_count == 0
    assert not result.top_countries and not result.actor_mentions
    assert all(row.source_id != "cisa_kev" for row in result.sources)
    assert all(row.count == 0 for row in result.counts)
    assert all(row.total == 0 for row in result.timeline)


async def test_actor_catalogue_disable_suppresses_derived_mentions_not_source_text():
    svc, _ = service((observation(title="APT28 and Fancy Bear mentioned"),))
    result = await snapshot(svc)
    assert result.actor_mentions[0].count == 1
    assert result.items[0].actor_mentions[0].group_id == ACTOR.group_id
    svc, _ = service((observation(title="APT28 mentioned"),), disabled=("mitre_attack",))
    result = await snapshot(svc)
    assert result.items[0].title == "APT28 mentioned"
    assert not result.actor_mentions and not result.items[0].actor_mentions


async def test_kevs_claims_and_outages_preserve_distinct_meanings_and_source_metadata():
    kev = observation(
        attributes=freeze_attributes(
            {
                "cve": "CVE-2026-12345",
                "vendor": "Example",
                "product": "Example product",
                "due_date": "2026-10-01",
                "ransomware": "Unknown",
                "cwes": "CWE-79",
                "required_action": "Apply vendor mitigations.",
            }
        )
    )
    claim = observation(
        "claim", source_id="ransomware_live", subtype="ransomware", country_iso="GB"
    )
    outage = observation("outage", source_id="ioda_outages", subtype="outage", country_iso=None)
    unrelated = observation("word", subtype="news", title="Ransomware report is merely a headline")
    svc, _ = service((kev, claim, outage, unrelated))
    result = await snapshot(svc)
    kinds = {row.id: row.kind for row in result.items}
    assert kinds[claim.id] is CyberKind.RANSOMWARE_CLAIM
    assert kinds[outage.id] is CyberKind.OUTAGE_SIGNAL and kinds[unrelated.id] is CyberKind.OTHER
    details = next(row.kev for row in result.items if row.id == kev.id)
    assert details.cve == "CVE-2026-12345" and details.ransomware_use == "Unknown"
    assert details.date_added == kev.published_at.date()
    assert details.required_action == "Apply vendor mitigations."
    assert result.top_countries[0].key == "GB" and result.top_countries[0].count == 1


@pytest.mark.parametrize(
    "url", [None, "javascript:alert(1)", "https://u:p@example.test", "https://["]
)
async def test_unsafe_links_are_excluded_from_counts_and_items(url):
    svc, _ = service((observation(url=url),))
    assert (await snapshot(svc)).retained_count == 0


async def test_all_disabled_sources_do_not_query_store():
    svc, admission = service()
    admission.enabled_many.side_effect = lambda ids: dict.fromkeys(ids, False)
    result = await snapshot(svc)
    assert result.sources == () and result.items == () and result.retained_count == 0


@pytest.mark.parametrize("value", [0, 1, 3, 6, 15, True, "2", 2.0])
def test_reject_unsupported_domain_windows(value):
    with pytest.raises(ValueError):
        cyber_window(value)


@pytest.mark.parametrize("kind", CyberKind)
def test_every_normalised_kind_is_recognised(kind):
    assert cyber_kind(kind.value) is kind


async def test_expensive_preparation_has_one_bounded_slot_and_no_waiting_queue(monkeypatch):
    svc, _ = service((observation(),))
    entered, release = asyncio.Event(), asyncio.Event()

    async def hold(work):
        entered.set()
        await release.wait()
        return work()

    monkeypatch.setattr(cyber_application, "joined_thread_call", hold)
    pending = asyncio.create_task(svc.read())
    await entered.wait()
    try:
        with pytest.raises(RateLimited):
            await svc.read()
    finally:
        release.set()
    assert (await pending).items
    assert (await svc.read()).items


async def test_unrecognised_kev_source_does_not_acquire_cisa_details():
    svc, _ = service((observation(source_id="ioda_outages"),))
    assert (await snapshot(svc)).items[0].kev is None


async def test_health_exposes_actual_success_and_failure_times_without_error_text():
    svc, _ = service()
    health = svc._health
    health.record_success("cisa_kev", 3, 20, NOW - timedelta(hours=1), timedelta(hours=1))
    health.record_failure("cisa_kev", "Upstream error details", NOW)
    result = await snapshot(svc)
    source = next(row for row in result.sources if row.source_id == "cisa_kev")
    assert source.status == "degraded"
    assert source.last_success == NOW - timedelta(hours=1) and source.last_error_at == NOW
    assert not hasattr(source, "last_error")

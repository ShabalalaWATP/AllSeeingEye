"""Provider independence, unknown scores, daily budgets and public rate backoff."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.kev_scores import EPSS_BATCH, KevScoreEnrichment
from ase.domain.events import freeze_attributes
from feeds_helpers import NOW, FakeClock, make_event

CVE = "CVE-2026-12345"


def kev(cve: str = CVE):
    return replace(
        make_event(cve), source_id="cisa_kev", attributes=freeze_attributes({"cve": cve})
    )


def epss():
    return {
        "data": [{"cve": CVE, "epss": "0.4", "percentile": "0.9", "date": NOW.date().isoformat()}]
    }


def nvd():
    return {
        "vulnerabilities": [
            {
                "cve": {
                    "id": CVE,
                    "lastModified": NOW.isoformat(),
                    "metrics": {
                        "cvssMetricV31": [
                            {
                                "type": "Primary",
                                "source": "nvd@nist.gov",
                                "cvssData": {
                                    "baseScore": 9.8,
                                    "version": "3.1",
                                    "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                                },
                            }
                        ]
                    },
                }
            }
        ]
    }


async def test_daily_scores_preserve_both_semantics_and_do_not_change_known_exploitation():
    http = AsyncMock()
    http.get_json.side_effect = [epss(), nvd()]
    clock = FakeClock(NOW)
    scores = KevScoreEnrichment(http, clock)
    first = (await scores.enrich([kev()]))[0]
    assert first.attributes["epss_probability"] == 0.4
    assert first.attributes["cvss_score"] == 9.8
    assert first.attributes["cvss_version"] == "3.1"
    assert first.severity == kev().severity
    assert first.content_hash != kev().content_hash
    assert (await scores.enrich([kev()]))[0].content_hash == first.content_hash
    assert http.get_json.await_count == 2


async def test_epss_failure_still_collects_cvss_and_reserves_daily_budget():
    http = AsyncMock()
    http.get_json.side_effect = [FeedFetchError("429"), nvd()]
    scores = KevScoreEnrichment(http, FakeClock(NOW))
    events = [kev(f"CVE-2026-{i:05}") for i in range(EPSS_BATCH + 1)] + [kev()]
    result = await scores.enrich(events)
    assert http.get_json.await_count == 2  # No second EPSS batch after a throttle.
    assert "epss_probability" not in result[-1].attributes
    assert result[-1].attributes["cvss_score"] == 9.8
    await scores.enrich(events)
    assert http.get_json.await_count == 2


async def test_nvd_failure_keeps_epss_and_does_not_invent_zero_severity():
    http = AsyncMock()
    http.get_json.side_effect = [epss(), FeedFetchError("unavailable")]
    event = (await KevScoreEnrichment(http, FakeClock(NOW)).enrich([kev()]))[0]
    assert event.attributes["epss_probability"] == 0.4
    assert "cvss_score" not in event.attributes


async def test_scores_refresh_after_24_hours_and_invalid_scores_remain_absent():
    http = AsyncMock()
    http.get_json.side_effect = [
        epss(),
        nvd(),
        {"data": [{"cve": CVE, "date": NOW.date().isoformat(), "epss": "NaN", "percentile": "1"}]},
        {"vulnerabilities": []},
    ]
    clock = FakeClock(NOW)
    scores = KevScoreEnrichment(http, clock)
    await scores.enrich([kev()])
    clock.advance(timedelta(days=1))
    result = (await scores.enrich([kev()]))[0]
    assert "epss_probability" not in result.attributes
    assert "cvss_score" not in result.attributes
    assert http.get_json.await_count == 4


async def test_malformed_nvd_metrics_preserve_valid_epss():
    http = AsyncMock()
    invalid = nvd()
    invalid["vulnerabilities"][0]["cve"]["metrics"] = {"cvssMetricV31": [None]}
    http.get_json.side_effect = [epss(), invalid]
    result = (await KevScoreEnrichment(http, FakeClock(NOW)).enrich([kev()]))[0]
    assert result.attributes["epss_probability"] == 0.4
    assert "cvss_score" not in result.attributes

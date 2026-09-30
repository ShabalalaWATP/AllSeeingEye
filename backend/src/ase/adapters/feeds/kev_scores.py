"""Daily, bounded FIRST EPSS and NVD severity context for already-known KEV records.

Scores describe different concepts. Neither changes CISA's known-exploited fact.
Failures never become zero scores. No retries, response-link traversal or disk cache.
"""

import asyncio
import json
import math
import re
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import structlog

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.application.ports import Clock
from ase.domain.events import Event, JsonScalar, content_hash, freeze_attributes

MAX_CVES = 1000
EPSS_BATCH = 100
NVD = "https://services.nvd.nist.gov/rest/json/cves/2.0"
EPSS = "https://api.first.org/data/v1/epss"
SCORE_KEYS = frozenset(
    {
        "epss_probability",
        "epss_percentile",
        "epss_date",
        "cvss_score",
        "cvss_version",
        "cvss_vector",
        "cvss_source",
        "cvss_date",
    }
)
log = structlog.get_logger(__name__)


def _score(value: Any, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, str | int | float):
        raise ValueError("Invalid vulnerability score")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= maximum:
        raise ValueError("Invalid vulnerability score")
    return number


def _epss(payload: Any, requested: set[str], today: date) -> dict[str, dict[str, JsonScalar]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("Invalid EPSS response")
    if len(payload["data"]) > EPSS_BATCH:
        raise ValueError("Oversized EPSS response")
    result: dict[str, dict[str, JsonScalar]] = {}
    for row in payload["data"]:
        if row["cve"] not in requested:
            continue
        score_date = date.fromisoformat(row["date"])
        if score_date > today:
            raise ValueError("Future EPSS date")
        result[row["cve"]] = {
            "epss_probability": _score(row["epss"], 1),
            "epss_percentile": _score(row["percentile"], 1),
            "epss_date": score_date.isoformat(),
        }
    return result


def _cvss(payload: Any, requested: set[str]) -> dict[str, dict[str, JsonScalar]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("vulnerabilities"), list):
        raise ValueError("Invalid NVD response")
    if len(payload["vulnerabilities"]) > MAX_CVES:
        raise ValueError("Oversized NVD response")
    result: dict[str, dict[str, JsonScalar]] = {}
    for item in payload["vulnerabilities"]:
        row = item["cve"]
        if row["id"] not in requested:
            continue
        modified = datetime.fromisoformat(row["lastModified"].replace("Z", "+00:00"))
        for kind in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            mapping = row.get("metrics", {})
            if not isinstance(mapping, dict):
                raise ValueError("Invalid NVD metric map")
            metrics = mapping.get(kind, [])
            if (
                not isinstance(metrics, list)
                or len(metrics) > 20
                or any(not isinstance(metric, dict) for metric in metrics)
            ):
                raise ValueError("Invalid NVD metrics")
            primary = next((metric for metric in metrics if metric.get("type") == "Primary"), None)
            metric = primary or next(iter(metrics), None)
            if metric is None:
                continue
            cvss = metric["cvssData"]
            version, vector, source = cvss["version"], cvss["vectorString"], metric["source"]
            if version not in {"2.0", "3.0", "3.1", "4.0"} or not all(
                isinstance(value, str) and 1 <= len(value) <= 300 for value in (vector, source)
            ):
                raise ValueError("Invalid NVD CVSS metadata")
            result[row["id"]] = {
                "cvss_score": _score(cvss["baseScore"], 10),
                "cvss_version": version,
                "cvss_vector": vector,
                "cvss_source": source,
                "cvss_date": modified.isoformat(),
            }
            break
    return result


class KevScoreEnrichment:
    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self.http, self.clock = http, clock
        self._next_run: datetime | None = None
        self._scores: dict[str, dict[str, JsonScalar]] = {}
        self._lock = asyncio.Lock()

    async def enrich(self, events: list[Event]) -> list[Event]:
        async with self._lock:
            now = self.clock.now()
            if self._next_run is None or now >= self._next_run:
                # Reserve the whole allowance before any await. Cancellation or a
                # provider error cannot trigger another burst in this process.
                self._next_run = now + timedelta(days=1)
                self._scores = {}
                await self._refresh(events, now)
            output = []
            for event in events:
                attributes = {
                    key: value for key, value in event.attributes.items() if key not in SCORE_KEYS
                }
                scores = self._scores.get(str(attributes.get("cve")), {})
                attributes.update(scores)
                output.append(
                    replace(
                        event,
                        attributes=freeze_attributes(attributes),
                        content_hash=content_hash(
                            event.content_hash, json.dumps(scores, sort_keys=True)
                        ),
                    )
                )
            return output

    async def _refresh(self, events: list[Event], now: datetime) -> None:
        cves = sorted(
            {
                str(event.attributes.get("cve"))
                for event in events
                if re.fullmatch(r"CVE-[0-9]{4}-[0-9]{4,9}", str(event.attributes.get("cve")))
            }
        )[:MAX_CVES]
        if not cves:
            return
        epss_requests = nvd_requests = failures = 0
        try:
            for start in range(0, len(cves), EPSS_BATCH):
                selected = set(cves[start : start + EPSS_BATCH])
                epss_requests += 1
                try:
                    query = urlencode({"cve": ",".join(sorted(selected)), "limit": EPSS_BATCH})
                    payload = await self.http.get_json(
                        f"{EPSS}?{query}",
                        conditional=False,
                        max_redirects=0,
                    )
                    self._scores.update(_epss(payload, selected, now.date()))
                except (FeedFetchError, ValueError, KeyError, TypeError):
                    failures += 1
                    break  # A throttle or failure stops this provider until tomorrow.
            params = {
                "hasKev": "",
                "kevStartDate": (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000"),
                "kevEndDate": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
                "resultsPerPage": str(MAX_CVES),
            }
            nvd_requests += 1
            try:
                payload = await self.http.get_json(
                    f"{NVD}?{urlencode(params)}", conditional=False, max_redirects=0
                )
                for cve, scores in _cvss(payload, set(cves)).items():
                    self._scores.setdefault(cve, {}).update(scores)
            except (FeedFetchError, ValueError, KeyError, TypeError):
                failures += 1
        finally:
            log.info(
                "kev_score_requests",
                epss_requests=epss_requests,
                nvd_requests=nvd_requests,
                failures=failures,
                daily_epss_cap=MAX_CVES // EPSS_BATCH,
                daily_nvd_cap=1,
            )

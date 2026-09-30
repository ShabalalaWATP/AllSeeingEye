"""Dated HDX HAPI v2 aggregates. One bounded request per selected topic.

The three fixed non-conflict endpoints are IOM DTM, IPC and OCHA context, not
ACLED conflict evidence. The application identifier encodes an operator email,
so it is sent only in an origin-bound header and never retained in evidence.
"""

import asyncio
import json
import math
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlencode
from uuid import UUID

from ase.adapters.feeds.http import FeedCredential, FeedFetchError, FeedHttpClient
from ase.adapters.research_records.records import receipt, record_event, text
from ase.application.ports import Clock
from ase.application.ports.research_capabilities import ProviderCapabilities
from ase.domain.events import Category, Event, GeoConfidence, JsonScalar, Reliability, content_hash
from ase.domain.observation import ObservationMetadata
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery

Topic = Literal["idps", "food-security", "operational-presence"]
TOPICS: tuple[Topic, ...] = ("idps", "food-security", "operational-presence")
PATHS = {
    "idps": "affected-people/idps",
    "food-security": "food-security-nutrition-poverty/food-security",
    "operational-presence": "coordination-context/operational-presence",
}
PUBLISHERS = {"idps": "IOM DTM", "food-security": "IPC", "operational-presence": "OCHA"}
ORIGIN = "https://hapi.humdata.org"
MAX_ROWS = 20
LIMITATIONS = (
    "One page of at most 20 HDX HAPI rows, not a complete administrative or national total. "
    "Reference periods and administrative levels are retained; period dates are not publication "
    "dates. No conflict-event endpoint or ACLED data is collected. HDX is a distributor, "
    "not independent corroboration of the underlying dataset. Consult the original HDX resource "
    "for methodology, revisions and dataset-specific reuse terms."
)


def _date(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Invalid HAPI period")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # HAPI v2 reference periods are documented date-times, often without offset.
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("Invalid HAPI quantity")
    if not math.isfinite(value) or not 0 <= value <= 1e12:
        raise ValueError("Invalid HAPI quantity")
    return float(value)


class HapiProvider:
    temporal_scope = "Dated administrative reference periods from one page of HDX HAPI data."

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        topic: Topic,
        countries: Mapping[str, str],
        app_identifier: str | None = None,
    ) -> None:
        self._http, self._clock, self.topic = http, clock, topic
        self._countries, self._identifier = countries, app_identifier
        self.id = f"research-hapi-{topic}"
        self.name = f"HDX HAPI {topic} ({PUBLISHERS[topic]})"

    def supports(self, query: ResearchQuery) -> bool:
        return (
            query.focus is ResearchFocus.GENERAL
            and query.area is None
            and query.country_iso in self._countries
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Select one supported country in general research.",
            )
        if not self._identifier:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "Configure an operator-generated HDX HAPI application identifier.",
            )
        params = {
            "location_code": self._countries[query.country_iso or ""],
            "start_date": query.since.date().isoformat(),
            "end_date": query.until.date().isoformat(),
            "limit": str(MAX_ROWS),
            "offset": "0",
            "output_format": "json",
        }
        url = f"{ORIGIN}/api/v2/{PATHS[self.topic]}?{urlencode(params)}"
        try:
            async with asyncio.timeout(20):
                payload = await self._http.get_json(
                    url,
                    conditional=False,
                    max_redirects=0,
                    credential=FeedCredential(
                        ORIGIN,
                        self._identifier,
                        header_name="X-HDX-HAPI-APP-IDENTIFIER",
                    ),
                )
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ValueError("Invalid HAPI v2 response")
            if len(payload["data"]) > MAX_ROWS:
                raise ValueError("HAPI response exceeds requested page")
            items = tuple(self._event(row, query) for row in payload["data"])
        except TimeoutError:
            return receipt(
                self.id, self.name, CollectionStatus.TIMED_OUT, "HAPI request timed out."
            )
        except (FeedFetchError, ValueError, KeyError, TypeError, OverflowError):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.FAILED,
                "HAPI request failed or returned an invalid bounded response. No retry.",
            )
        return receipt(
            self.id,
            self.name,
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            LIMITATIONS,
            items,
        )

    def _event(self, row: Any, query: ResearchQuery) -> Event:
        if (
            not isinstance(row, dict)
            or row.get("location_code") != self._countries[query.country_iso or ""]
        ):
            raise ValueError("HAPI country mismatch")
        resource = str(UUID(row["resource_hdx_id"]))
        level = row["admin_level"]
        if type(level) is not int or level not in (0, 1, 2):
            raise ValueError("Invalid HAPI administrative level")
        start, end = _date(row["reference_period_start"]), _date(row["reference_period_end"])
        if start is None or (end is not None and end < start):
            raise ValueError("Missing or invalid HAPI period")
        if start >= query.until or (end is not None and end < query.since):
            raise ValueError("HAPI period does not overlap request")
        attributes: dict[str, JsonScalar] = {
            "record_kind": "humanitarian_aggregate",
            "dataset_resource_id": resource,
            "publisher": PUBLISHERS[self.topic],
            "distributor": "HDX HAPI",
            "admin_level": level,
            "admin1_code": text(row.get("admin1_code")),
            "admin1_name": text(row.get("admin1_name")),
            "admin2_code": text(row.get("admin2_code")),
            "admin2_name": text(row.get("admin2_name")),
            "period_start": start.isoformat(),
            "period_end": end.isoformat() if end else None,
            "unit": "people",
            "independent_conflict_corroboration": False,
        }
        if self.topic == "idps":
            if (
                type(row["reporting_round"]) is not int
                or not 0 <= row["reporting_round"] <= 1_000_000
            ):
                raise ValueError("Invalid HAPI reporting round")
            attributes.update(
                value=_number(row["population"]),
                reporting_round=row["reporting_round"],
                assessment_type=text(row["assessment_type"]),
                operation=text(row["operation"]),
            )
        elif self.topic == "food-security":
            fraction = _number(row["population_fraction_in_phase"])
            if fraction > 1:
                raise ValueError("Invalid HAPI population fraction")
            attributes.update(
                value=_number(row["population_in_phase"]),
                population_fraction=fraction,
                ipc_phase=text(row["ipc_phase"]),
                ipc_type=text(row["ipc_type"]),
            )
        else:
            attributes.update(
                value=1,
                unit="organisation-sector-location record",
                organisation=text(row["org_name"]),
                sector=text(row["sector_name"]),
            )
        key = content_hash(json.dumps(attributes, sort_keys=True))
        event = record_event(
            self.id,
            key,
            f"{PUBLISHERS[self.topic]} {self.topic}: {row['location_code']}",
            f"{attributes['value']} {attributes['unit']}, administrative level {level}, "
            f"reference period {start.isoformat()} to {end.isoformat() if end else 'unspecified'}. "
            "This is one source record; overlapping rows must not be summed "
            "without reconciliation.",
            f"https://data.humdata.org/api/3/action/resource_show?id={resource}",
            self._clock.now(),
            category=Category.HUMANITARIAN,
            attributes=attributes,
        )
        return replace(
            event,
            published_at=None,
            content_hash=key,
            country_iso=query.country_iso,
            geo_confidence=GeoConfidence.COUNTRY,
            reliability=Reliability.F,
            observation=ObservationMetadata(start, resource, key, LIMITATIONS),
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(temporal_scope=self.temporal_scope)

"""Opt-in current Cloudflare distributions, never historical search or incident evidence.

Contract reviewed 2026-09-14:
https://developers.cloudflare.com/radar/investigate/application-layer-attacks/
https://developers.cloudflare.com/api/resources/radar/subresources/attacks/subresources/layer3/subresources/top/subresources/locations/methods/target/
https://radar.cloudflare.com/about

Composition shares the existing reader and applies current source controls. Each selected
layer makes at most one fixed endpoint request on a cache miss; query text never reaches Radar.
"""

import asyncio
import math
import re
from datetime import timedelta

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.radar_attack_trends import (
    Layer,
    RadarAttackSnapshot,
    RadarAttackTrends,
)
from ase.adapters.research_records.cloudflare_radar_records import radar_record
from ase.adapters.research_records.records import receipt
from ase.application.ports import Clock
from ase.application.ports.research_capabilities import ProviderCapabilities
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import CollectionStatus, ResearchBatch, ResearchFocus, ResearchQuery
from ase.domain.research_scope import COUNTRY_CODES

PROVIDER_IDS = {
    "layer3": "research-cloudflare-radar-layer3",
    "layer7": "research-cloudflare-radar-layer7",
}
_RECENT = timedelta(hours=2)
_TIMEOUT_SECONDS = 15
_LIMITATIONS = (
    "Current global top-10 target-country ranking for the selected layer only; no historical "
    "search, query-text filtering or complete country coverage. Shares describe Cloudflare's "
    "provider-defined traffic, not incident counts, local prevalence or attribution. "
    "Country selection filters the global ranking without changing its denominator. "
    "Provider intervals are retained whole, never clipped or extrapolated. Missing countries "
    "are unknown, not zero. Cloudflare Radar; CC BY-NC 4.0, noncommercial use and attribution. "
)


class CloudflareRadarResearchProvider:
    language = "en"
    temporal_scope = "Current provider-defined one-day aggregate, not historical-window search."

    def __init__(
        self,
        reader: RadarAttackTrends,
        clock: Clock,
        *,
        layer: Layer,
        allow_noncommercial_data: bool = False,
    ) -> None:
        if layer not in PROVIDER_IDS:
            raise ValueError("Unsupported Radar research layer")
        self.id, self.name = PROVIDER_IDS[layer], f"Cloudflare Radar {layer} target distribution"
        self.layer = layer
        self._reader, self._clock = reader, clock
        self._allowed = allow_noncommercial_data is True

    def _selection(self, query: ResearchQuery) -> str | None:
        if (
            query.focus is not ResearchFocus.GENERAL
            or query.area is not None
            or len(query.country_isos) > 1
            or "en" not in query.languages
            or query.effective_time_basis
            not in (EvidenceTimeBasis.RESEARCH, EvidenceTimeBasis.RECORDED)
            or (query.source_ids is not None and self.id not in query.source_ids)
        ):
            return None
        subject = (query.subject or "").strip()
        match = re.fullmatch(r"radar:(global|[A-Z]{2})", subject)
        if subject and match is None:
            return None
        if match is not None:
            selected = match[1]
            valid = (selected == "global" or selected in COUNTRY_CODES) and (
                not query.country_iso or selected == query.country_iso
            )
            return selected if valid else None
        if query.source_ids and self.id in query.source_ids:
            return query.country_iso or "global"
        return None

    def supports(self, query: ResearchQuery) -> bool:
        now = self._clock.now()
        return (
            self._selection(query) is not None
            and query.since <= now - timedelta(days=1)
            and now - _RECENT <= query.until <= now + timedelta(minutes=1)
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:  # noqa: PLR0911
        """Each early exit retains a distinct no-coverage receipt for the caller."""
        selected = self._selection(query)
        if selected is None or not self.supports(query):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNSUPPORTED,
                "Select this source or radar:global/radar:CC with global or one-country scope, "
                "English and observation/recorded-time retrieval. Only current one-day "
                "rankings are available; historical, polygon and entity scopes are unsupported. "
                "No reader call was made.",
            )
        if not self._allowed:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.UNAVAILABLE,
                "Cloudflare Radar API data needs explicit operator acknowledgement of "
                "CC BY-NC 4.0 noncommercial use and attribution. No reader call was made.",
            )
        try:
            async with asyncio.timeout(_TIMEOUT_SECONDS):
                snapshot = await self._reader.read_layer(self.layer)
            if snapshot.status in {"not_configured", "disabled", "unavailable", "stale"}:
                return receipt(
                    self.id,
                    self.name,
                    CollectionStatus.UNAVAILABLE,
                    f"Cloudflare Radar state is {snapshot.status}; current permitted coverage "
                    "was not established. A configured Radar read token is required.",
                )
            self._validate(snapshot)
            layers = tuple(
                layer
                for layer in snapshot.layers
                if query.since <= layer.period_from and layer.period_to < query.until
            )
            if not layers:
                return receipt(
                    self.id,
                    self.name,
                    CollectionStatus.UNSUPPORTED,
                    "Returned Radar intervals are outside the requested half-open interval. "
                    "Inclusive provider end bounds were preserved; no aggregate was clipped.",
                )
            items = tuple(
                radar_record(self.id, layer, country, snapshot, query)
                for layer in layers
                for country in layer.countries
                if selected in ("global", country.country_iso)
            )
            note = _LIMITATIONS + (
                f"Collected {self.layer} only; reader status {snapshot.status}. "
                "Dataset version is absent where the provider does not return meta.version."
            )
            return receipt(
                self.id,
                self.name,
                CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
                note,
                items,
            )
        except TimeoutError:
            return receipt(
                self.id,
                self.name,
                CollectionStatus.TIMED_OUT,
                "Cloudflare Radar snapshot read timed out; no evidence was released.",
            )
        except (FeedFetchError, OSError, ValueError, TypeError, AttributeError, OverflowError):
            return receipt(
                self.id,
                self.name,
                CollectionStatus.FAILED,
                "Cloudflare Radar returned unavailable or invalid aggregate data; "
                "no coverage was established.",
            )

    def _validate(self, snapshot: RadarAttackSnapshot) -> None:
        now = self._clock.now()
        fetched = snapshot.fetched_at
        if (
            snapshot.status != "ready"
            or fetched is None
            or fetched.utcoffset() is None
            or not now - _RECENT <= fetched <= now
            or len(snapshot.layers) != 1
        ):
            raise ValueError("Invalid Radar snapshot metadata")
        for layer in snapshot.layers:
            if (
                layer.layer != self.layer
                or layer.period_from.utcoffset() is None
                or layer.period_to.utcoffset() is None
                or not timedelta(0) < layer.period_to - layer.period_from <= timedelta(days=1)
                or not fetched - _RECENT <= layer.period_to <= fetched
                or layer.updated_at is None
                or layer.updated_at.utcoffset() is None
                or not layer.period_to <= layer.updated_at <= fetched
                or len(layer.provider_units) != 1
                or layer.provider_units[0].name != "*"
                or layer.provider_units[0].value != layer.unit
                or layer.unit not in {"bytes", "requests"}
                or (layer.layer == "layer7" and layer.unit != "requests")
                or not 1 <= len(layer.countries) <= 10
                or (
                    layer.provider_version is not None
                    and (
                        not 1 <= len(layer.provider_version) <= 100
                        or any(ord(char) < 32 for char in layer.provider_version)
                    )
                )
            ):
                raise ValueError("Invalid Radar layer metadata")
            countries = layer.countries
            if (
                len({row.country_iso for row in countries}) != len(countries)
                or {row.rank for row in countries} != set(range(1, len(countries) + 1))
                or any(
                    row.country_iso not in COUNTRY_CODES
                    or type(row.rank) is not int
                    or not isinstance(row.country_name, str)
                    or not row.country_name.strip()
                    or len(row.country_name) > 80
                    or type(row.share_percent) not in (int, float)
                    or not math.isfinite(row.share_percent)
                    or not 0 <= row.share_percent <= 100
                    for row in countries
                )
                or math.fsum(row.share_percent for row in countries) > 100.0001
            ):
                raise ValueError("Invalid Radar country distribution")

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            language=self.language,
            temporal_scope=self.temporal_scope,
        )

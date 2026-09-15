"""No DNS, credentials or live Radar calls: synthetic provider-response fixtures only."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ase.adapters.feeds.radar_attack_trends import RadarAttackTrends
from ase.adapters.research_records.cloudflare_radar import (
    PROVIDER_IDS,
    CloudflareRadarResearchProvider,
)
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import ResearchQuery
from helpers import FakeClock

NOW = datetime(2026, 9, 14, 10, tzinfo=UTC)
QUERY = ResearchQuery(
    question="Private decision question which must never reach Radar",
    since=NOW - timedelta(days=3),
    until=NOW,
    terms=("private investigation",),
    source_ids=tuple(PROVIDER_IDS.values()),
    time_basis=EvidenceTimeBasis.RESEARCH,
)
FIXTURE = Path(__file__).parent / "fixtures" / "research" / "cloudflare_radar_attacks.json"


def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class RadarHttp:
    def __init__(self, data=None):
        self.data, self.calls = data or payload(), []

    async def get_json(self, url, *, credential, conditional, max_redirects):
        assert not conditional and max_redirects == 0
        assert credential.origin == "https://api.cloudflare.com"
        self.calls.append(url)
        return self.data["layer7" if "/layer7/" in url else "layer3"]


def provider(data=None, *, layer="layer3", allowed=True, token="offline-fixture-token"):  # noqa: S107
    """The default token is a synthetic offline marker, never a configured credential."""
    http, clock = RadarHttp(data), FakeClock(NOW)
    reader = RadarAttackTrends(http, clock, token)
    return CloudflareRadarResearchProvider(
        reader, clock, layer=layer, allow_noncommercial_data=allowed
    ), http

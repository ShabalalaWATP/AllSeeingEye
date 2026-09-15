"""Pure Radar aggregate records with exact provider metadata and no inferred incidents."""

import json

from ase.adapters.feeds.radar_attack_trends import (
    SPEC,
    RadarAttackCountry,
    RadarAttackLayer,
    RadarAttackSnapshot,
)
from ase.domain.events import (
    Category,
    Event,
    GeoConfidence,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.observation import ObservationMetadata
from ase.domain.research import ResearchQuery

LICENCE = "CC BY-NC 4.0"
LICENCE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"
TERMS_URL = "https://radar.cloudflare.com/about"


def radar_record(
    source_id: str,
    layer: RadarAttackLayer,
    country: RadarAttackCountry,
    snapshot: RadarAttackSnapshot,
    query: ResearchQuery,
) -> Event:
    if snapshot.fetched_at is None or layer.updated_at is None:
        raise ValueError("Radar evidence requires retrieval and dataset-update timestamps")
    endpoint = (
        f"https://api.cloudflare.com/client/v4/radar/attacks/{layer.layer}/top/locations/target"
    )
    key = (
        f"{layer.layer}:{layer.period_from.isoformat()}:"
        f"{layer.period_to.isoformat()}:{country.country_iso}"
    )
    units = json.dumps(
        [{"name": unit.name, "value": unit.value} for unit in layer.provider_units],
        separators=(",", ":"),
    )
    geography = (
        "Target billing country of the protected zone"
        if layer.layer == "layer7"
        else "Provider-defined target-country aggregate"
    )
    metadata = freeze_attributes(
        {
            "original_source_id": SPEC.id,
            "publisher": "Cloudflare Radar",
            "record_kind": "network_attack_distribution",
            "layer": layer.layer,
            "period_start": layer.period_from.isoformat(),
            "period_end": layer.period_to.isoformat(),
            "period_end_inclusive": True,
            "date_basis": "provider_aggregate_interval",
            "retrieved_at": snapshot.fetched_at.isoformat(),
            "dataset_updated_at": layer.updated_at.isoformat(),
            "api_version": "v4",
            "provider_version": layer.provider_version,
            "provider_units": units,
            "unit": "%",
            "denominator_unit": layer.unit,
            "normalization": "PERCENTAGE",
            "share_percent": country.share_percent,
            "rank": country.rank,
            "country_name": country.country_name,
            "geography_basis": geography,
            "query_since": query.since.isoformat(),
            "query_until": query.until.isoformat(),
            "snapshot_status": snapshot.status,
            "global_rank_limit": 10,
            "licence": LICENCE,
            "licence_url": LICENCE_URL,
            "terms_url": TERMS_URL,
            "attribution": "Cloudflare Radar",
            "attribution_status": "not_established",
        }
    )
    summary = (
        f"Cloudflare Radar returned rank {country.rank} and share {country.share_percent}% "
        f"for {country.country_name} in {layer.layer} target-country rankings. "
        f"Provider denominator unit: {layer.unit}; normalized percentage, not a raw count. "
        f"Interval {layer.period_from.isoformat()} to {layer.period_to.isoformat()} "
        f"(provider inclusive end). {geography}. No precise target incidents or actor "
        "attribution are established. Cloudflare Radar, CC BY-NC 4.0."
    )
    return Event(
        id=event_id(source_id, key),
        source_id=source_id,
        category=Category.CYBER,
        subtype="attack_distribution",
        title=f"Radar {layer.layer}: {country.country_name} "
        f"rank {country.rank}, share {country.share_percent}%",
        summary=summary,
        url=endpoint,
        published_at=None,
        observed_at=snapshot.fetched_at,
        reliability=Reliability.F,
        country_iso=country.country_iso,
        geo_confidence=GeoConfidence.COUNTRY,
        attributes=metadata,
        observation=ObservationMetadata(
            layer.period_from,
            endpoint,
            key,
            "Time anchor is the provider aggregate's start, not an incident instant. "
            "Exact interval retained in period_start/period_end; "
            "lastUpdated is not publication.",
            processed_at=layer.updated_at,
        ),
        grade_rationale="Provider-reported traffic distribution; inference remains unassessed.",
        tags=frozenset({"research_record", "aggregate", "cloudflare_radar"}),
        content_hash=content_hash(
            summary,
            json.dumps(
                {
                    key: value
                    for key, value in metadata.items()
                    if key not in {"query_since", "query_until", "retrieved_at", "snapshot_status"}
                },
                sort_keys=True,
            ),
        ),
    )

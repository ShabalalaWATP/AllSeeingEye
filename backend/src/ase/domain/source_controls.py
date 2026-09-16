"""Source variants and sensor families inherit their configured parent admission."""


def source_control_keys(source_id: str) -> tuple[str, ...]:
    if source_id in {
        "research-cloudflare-radar-layer3",
        "research-cloudflare-radar-layer7",
    }:
        return (source_id, "cloudflare_radar_attack_trends")
    parent = {
        "research-ioda-outage-events": "ioda_outage_events",
        "research-usgs-area": "usgs_earthquakes",
        "research-eonet-area": "nasa_eonet",
    }.get(source_id)
    if parent is not None:
        return (source_id, parent)
    if source_id in {"firms_viirs_noaa21", "firms_public_noaa21"}:
        return (source_id, source_id.replace("noaa21", "noaa20"))
    if source_id.startswith("research_google_news_"):
        return (source_id, "google_news")
    for prefix in ("research_regional_", "research_publisher_"):
        if source_id.startswith(prefix):
            return (source_id, source_id.removeprefix(prefix))
    return (source_id,)

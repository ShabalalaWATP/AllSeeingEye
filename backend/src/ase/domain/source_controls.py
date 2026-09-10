"""Source variants and sensor families inherit their configured parent admission."""


def source_control_keys(source_id: str) -> tuple[str, ...]:
    if source_id in {"research-usgs-area", "research-eonet-area"}:
        return (
            source_id,
            "usgs_earthquakes" if source_id == "research-usgs-area" else "nasa_eonet",
        )
    if source_id in {"firms_viirs_noaa21", "firms_public_noaa21"}:
        return (source_id, source_id.replace("noaa21", "noaa20"))
    if source_id.startswith("research_google_news_"):
        return (source_id, "google_news")
    for prefix in ("research_social_", "research_regional_", "research_publisher_"):
        if source_id.startswith(prefix):
            return (source_id, source_id.removeprefix(prefix))
    return (source_id,)

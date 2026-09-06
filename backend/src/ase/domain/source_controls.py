"""On-demand source variants inherit their configured parent source admission."""


def source_control_keys(source_id: str) -> tuple[str, ...]:
    if source_id.startswith("research_google_news_"):
        return (source_id, "google_news")
    for prefix in ("research_social_", "research_regional_"):
        if source_id.startswith(prefix):
            return (source_id, source_id.removeprefix(prefix))
    return (source_id,)

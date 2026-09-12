"""Conservative policy and reusable rows for the expanded public news catalogue."""

from dataclasses import replace

from ase.adapters.feeds.rss import RssOptions
from ase.adapters.feeds.rss_seeds import RssSeed, seed
from ase.domain.events import Category, Credibility, Reliability
from ase.domain.source_ratings import COMMON_LIMITATIONS, SOURCE_RATING_POLICY_VERSION, SourceRating

NEWS_OPTIONS = RssOptions(
    tags=frozenset({"publisher_news", "headlines_only"}),
    credibility=Credibility.CANNOT_BE_JUDGED,
    rationale="Publisher-attributed headline; source reliability and claim remain unassessed.",
    headlines_only=True,
    newest_first=True,
)
NEWS_TERMS = (
    "Publisher RSS terms apply. Headlines, attribution, publication dates and links only; "
    "no article text or imagery retained. Public access does not establish commercial reuse "
    "rights. Retained headlines may inform reports; no private publisher search or archive."
)
PERSONAL_TERMS = "Publisher restricts RSS to personal, non-commercial use. " + NEWS_TERMS


def news_seed(
    key: str,
    name: str,
    organisation: str,
    url: str,
    homepage: str,
    scope: str,
    *,
    language: str = "en",
    terms: str = NEWS_TERMS,
    flags: frozenset[str] = frozenset(),
) -> RssSeed:
    row = seed(
        f"news_{key}",
        name,
        organisation,
        Category.NEWS,
        url,
        Reliability.F,
        30,
        NEWS_OPTIONS,
        homepage=homepage,
        language=language,
        licence_note=terms,
        flags=flags | {"unassessed", "headlines_only", "retained_feed_research"},
    )
    rating = SourceRating(
        policy_version=SOURCE_RATING_POLICY_VERSION,
        status="unassessed",
        assessed_grade=None,
        basis=f"{name} publishes this public RSS feed; endpoint availability does not "
        "establish publisher reliability or verify its individual claims.",
        scope=scope + " Publisher coverage does not establish incident geography.",
        limitations=(
            *COMMON_LIMITATIONS,
            "One bounded feed snapshot, not a complete archive. Retained headlines only; "
            "shared ownership and syndicated reporting do not add independent corroboration.",
        ),
        provenance_role="publisher",
        publisher_reliability_assessed=False,
    )
    return replace(row, spec=replace(row.spec, rating=rating))

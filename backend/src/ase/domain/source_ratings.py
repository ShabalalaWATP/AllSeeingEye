"""Transparent qualitative source-rating metadata, independent of scoring behaviour."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from ase.domain.events import Reliability
from ase.domain.source_rating_catalog import CATALOGUE, ProvenanceRole

SOURCE_RATING_POLICY_VERSION = "ase-source-ratings-v1"
COMMON_LIMITATIONS = (
    "The configured grade is an inherited editorial policy, not independently revalidated "
    "performance, a measured accuracy percentage or a guarantee about an individual claim.",
    "Source reliability and item credibility are separate. Missing or unknown assessment "
    "does not mean that information is false.",
    "No historical review date is recorded; publication and capture times are not review dates.",
)


@dataclass(frozen=True, slots=True)
class SourceRating:
    policy_version: str
    status: Literal["editorial", "unassessed"]
    assessed_grade: Reliability | None
    basis: str
    scope: str
    limitations: tuple[str, ...]
    provenance_role: ProvenanceRole
    publisher_reliability_assessed: bool
    reviewed_at: datetime | None = None


def unassessed_source_rating() -> SourceRating:
    return SourceRating(
        policy_version=SOURCE_RATING_POLICY_VERSION,
        status="unassessed",
        assessed_grade=None,
        basis="No source-specific reliability assessment basis is recorded.",
        scope="Unassessed source identity and publication context.",
        limitations=COMMON_LIMITATIONS,
        provenance_role="unassessed",
        publisher_reliability_assessed=False,
    )


def _platform_rating(configured_grade: Reliability) -> SourceRating:
    return SourceRating(
        policy_version=SOURCE_RATING_POLICY_VERSION,
        status="unassessed",
        assessed_grade=None,
        basis=f"The retained {configured_grade.value} feed grade is a legacy collection caution, "
        "not an assessment "
        "of each public post's author. Author reliability remains unassessed.",
        scope="Public posts exposed by a configured community or instance.",
        limitations=(
            *COMMON_LIMITATIONS,
            "A platform, subreddit or instance does not confer publisher credibility. "
            "Accounts, repost origins and item claims require their own attribution.",
            "Timeline selection, moderation and federation affect coverage. No platform-wide "
            "sampling or account authentication is performed.",
        ),
        provenance_role="platform",
        publisher_reliability_assessed=False,
    )


def source_rating_for(source_id: str, configured_grade: Reliability) -> SourceRating:
    """Describe registered assignments; never infer reliability from a domain or platform."""
    if source_id.startswith(("mastodon_", "telegram_")) or source_id in {
        "reddit_worldnews",
        "reddit_geopolitics",
        "reddit_ukrainianconflict",
    }:
        return _platform_rating(configured_grade)
    entry = CATALOGUE.get(source_id)
    if entry is None:
        return unassessed_source_rating()
    if configured_grade.value != entry.grade:
        return SourceRating(
            policy_version=SOURCE_RATING_POLICY_VERSION,
            status="unassessed",
            assessed_grade=None,
            basis=f"Configured grade {configured_grade.value} differs from the inherited registry "
            f"assignment {entry.grade}; no source-specific reassessment basis is recorded.",
            scope=entry.scope,
            limitations=(*COMMON_LIMITATIONS, *entry.limitations),
            provenance_role=entry.role,
            publisher_reliability_assessed=False,
        )
    return SourceRating(
        policy_version=SOURCE_RATING_POLICY_VERSION,
        status="editorial",
        assessed_grade=configured_grade,
        basis=entry.basis,
        scope=entry.scope,
        limitations=(*COMMON_LIMITATIONS, *entry.limitations),
        provenance_role=entry.role,
        publisher_reliability_assessed=entry.role in ("originator", "publisher"),
    )

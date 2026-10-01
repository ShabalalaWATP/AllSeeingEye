"""Saved-report discovery groups and the effective origin of a stored report scope."""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from ase.domain.reports import ReportOrigin

# Discovery lists cover at most the caller's latest visible reports in a group; the
# section views keep reaching older reports through their own origin filter.
DISCOVERY_WINDOW = 1000


class ReportGroup(StrEnum):
    """Named sets of origins. Requested work never includes automatic briefings."""

    REQUESTED = "requested"


REQUESTED_ORIGINS: tuple[ReportOrigin, ...] = (
    ReportOrigin.RESEARCH,
    ReportOrigin.SUBSCRIPTION,
    ReportOrigin.GEOLOCATION,
)

GROUP_ORIGINS: Mapping[ReportGroup, tuple[ReportOrigin, ...]] = {
    ReportGroup.REQUESTED: REQUESTED_ORIGINS,
}


def effective_origin(scope: Mapping[str, Any]) -> ReportOrigin:
    """A recognised stated origin wins; older scopes keep the media/research fallback.

    Mirrors the SQL classification used to filter saved report lists.
    """
    stated = scope.get("origin")
    if isinstance(stated, str) and stated in {value.value for value in ReportOrigin}:
        return ReportOrigin(stated)
    if scope.get("research_focus") == "media":
        return ReportOrigin.GEOLOCATION
    return ReportOrigin.RESEARCH

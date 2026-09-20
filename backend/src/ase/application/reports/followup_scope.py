"""Keep inherited evidence attached to the geographical and fixed historical scope."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ase.application.reports.request import ReportRequest
from ase.domain.errors import InvalidRequest
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.map_research_origin import origin_from_dict
from ase.domain.regions import normalise_regions
from ase.domain.research_area import area_from_dict
from ase.domain.research_scope import normalise_countries


def require_followup_scope(scope: Mapping[str, Any], request: ReportRequest) -> None:
    try:
        countries = normalise_countries(scope.get("country"), scope.get("countries", ()))
        regions = normalise_regions(scope.get("regions", ()))
        since = (
            datetime.fromisoformat(str(scope["research_since"]))
            if scope.get("research_since")
            else None
        )
        until = (
            datetime.fromisoformat(str(scope["research_until"]))
            if scope.get("research_until")
            else None
        )
        if (since is None) != (until is None):
            raise ValueError("Incomplete saved interval")
        if (
            since is not None
            and until is not None
            and (since.utcoffset() is None or until.utcoffset() is None or since >= until)
        ):
            raise ValueError("Invalid saved interval")
        saved_area = area_from_dict(scope.get("research_area"))
        map_origin = origin_from_dict(scope.get("map_origin"))
        if saved_area is not None and map_origin is not None:
            raise ValueError("Ambiguous saved area")
        saved_area = saved_area or (map_origin.area if map_origin is not None else None)
        saved_basis = (
            EvidenceTimeBasis(str(scope["research_time_basis"]))
            if scope.get("research_time_basis")
            else EvidenceTimeBasis.RESEARCH
            if saved_area is not None
            else EvidenceTimeBasis.PUBLICATION
        )
    except (ValueError, TypeError) as exc:
        raise InvalidRequest("The saved report has an invalid research scope") from exc
    if saved_basis is EvidenceTimeBasis.RECORDED and (
        (request.research_since, request.research_until) != (since, until)
        or request.effective_time_basis is not saved_basis
    ):
        raise InvalidRequest(
            "A historical follow-up must retain its recorded period and time basis"
        )
    if frozenset(request.country_isos) != frozenset(countries):
        raise InvalidRequest(
            "A follow-up must retain the saved report's countries; "
            "start new research to change them"
        )
    if frozenset(request.regions) != frozenset(regions):
        raise InvalidRequest(
            "A follow-up must retain the saved report's regions; start new research to change them"
        )
    if request.effective_area != saved_area:
        raise InvalidRequest("Area research follow-up must retain the exact saved area")
    if (request.research_since, request.research_until) != (since, until):
        raise InvalidRequest(
            "A follow-up must retain its saved fixed interval; start new research to change dates"
        )
    if request.effective_time_basis is not saved_basis:
        raise InvalidRequest(
            "A follow-up must retain the saved evidence time basis; start new research to change it"
        )
    if saved_area is not None and not request.disclose_area_to_provider:
        raise InvalidRequest("Area follow-up requires the saved disclosure choice")

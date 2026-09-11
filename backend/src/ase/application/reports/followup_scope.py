"""Keep inherited evidence attached to the geographical and fixed historical scope."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ase.application.reports.request import ReportRequest
from ase.domain.errors import InvalidRequest
from ase.domain.research_scope import normalise_countries


def require_followup_scope(scope: Mapping[str, Any], request: ReportRequest) -> None:
    try:
        countries = normalise_countries(scope.get("country"), scope.get("countries", ()))
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
    except (ValueError, TypeError) as exc:
        raise InvalidRequest("The saved report has an invalid research scope") from exc
    if frozenset(request.country_isos) != frozenset(countries):
        raise InvalidRequest(
            "A follow-up must retain the saved report's countries; "
            "start new research to change them"
        )
    if (request.research_since, request.research_until) != (since, until):
        raise InvalidRequest(
            "A follow-up must retain its saved fixed interval; start new research to change dates"
        )

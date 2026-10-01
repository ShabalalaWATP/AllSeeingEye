"""One SQL classification of where a report or job was asked for.

Recognised explicit origins win. Older or unrecognised scopes keep the media/research
classification used by saved report links, so legacy records stay reachable.
"""

from typing import Any

from sqlalchemy import JSON, ColumnElement, String, case, cast, func
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.domain.reports import ReportOrigin


def effective_origin(stated: ColumnElement[Any], focus: ColumnElement[Any]) -> ColumnElement[str]:
    return case(
        (stated.in_([value.value for value in ReportOrigin]), stated),
        (focus == "media", ReportOrigin.GEOLOCATION.value),
        else_=ReportOrigin.RESEARCH.value,
    )


def _job_scope(session: AsyncSession, key: str) -> ColumnElement[Any]:
    """A frozen job's scope field, read from the integrity-checked checkpoint text."""
    if session.get_bind().dialect.name == "sqlite":
        return func.json_extract(ReportJobRow.payload, f"$.input.scope.{key}", type_=String)
    value: ColumnElement[Any] = cast(ReportJobRow.payload, JSON)[
        ("input", "scope", key)
    ].as_string()
    return value


def job_origin(session: AsyncSession) -> ColumnElement[str]:
    return effective_origin(_job_scope(session, "origin"), _job_scope(session, "research_focus"))

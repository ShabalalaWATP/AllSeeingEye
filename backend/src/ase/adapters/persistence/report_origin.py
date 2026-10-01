"""Classify a polling row from its bounded, validated checkpoint projection."""

from typing import Any

from sqlalchemy import ColumnElement, case, literal
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_job_projection import POLLING_ORIGINS
from ase.domain.reports import ReportOrigin


def effective_origin(stated: ColumnElement[Any], focus: ColumnElement[Any]) -> ColumnElement[str]:
    return case(
        (stated.in_(sorted(POLLING_ORIGINS)), stated),
        (focus == "media", ReportOrigin.GEOLOCATION.value),
        else_=ReportOrigin.RESEARCH.value,
    )


def job_origin(session: AsyncSession) -> ColumnElement[str]:
    """Keep the listing API while using SQLAlchemy's portable JSON-column extraction.

    Write and migration projections already resolved legacy media/research origins.
    Never cast or inspect the potentially large checkpoint text during polling.
    """
    return effective_origin(ReportJobRow.summary["origin"].as_string(), literal(None))

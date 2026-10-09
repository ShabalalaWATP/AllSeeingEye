"""Strict codec for the internal alert origin retained in report scope."""

from typing import Any, cast

from pydantic import TypeAdapter

from ase.application.report_jobs.codec_boundary import canonical
from ase.domain.alert_reports import AlertReportOrigin

_ORIGIN = TypeAdapter(AlertReportOrigin)


def origin_to_dict(origin: AlertReportOrigin) -> dict[str, Any]:
    return cast(dict[str, Any], _ORIGIN.dump_python(origin, mode="json"))


def origin_from_dict(value: Any) -> AlertReportOrigin | None:
    if value is None:
        return None
    origin = _ORIGIN.validate_python(value)
    canonical(value, origin_to_dict(origin))
    return origin

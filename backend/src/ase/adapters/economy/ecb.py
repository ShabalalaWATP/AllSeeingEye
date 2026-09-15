"""ECB 90-day reference rates.

XML parsing uses defusedxml; stdlib Element and ParseError are type/exception names only.
"""

import math
from dataclasses import replace
from datetime import date, datetime, timedelta
from xml.etree.ElementTree import Element, ParseError  # nosec B405

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from ase.domain.economy import EconomyPoint, EconomySeries
from ase.domain.economy_catalogue import FX_NOTE, empty_fx

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
ECB_NAMESPACE = "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"
MAX_XML_BYTES = 512 * 1024


def parse_ecb(raw: bytes, now: datetime) -> tuple[EconomySeries, ...]:
    if len(raw) > MAX_XML_BYTES:
        raise ValueError("Exchange-rate document exceeds the size limit")
    try:
        root = ElementTree.fromstring(raw, forbid_dtd=True)
    except (ParseError, DefusedXmlException):
        raise ValueError("Invalid exchange-rate document") from None
    periods = root.findall(f".//{{{ECB_NAMESPACE}}}Cube[@time]")
    if not 1 <= len(periods) <= 90:
        raise ValueError("Invalid exchange-rate period count")
    values = _rates(periods, now)
    result = []
    for item in empty_fx():
        if item.id not in values:
            result.append(item)
            continue
        points = tuple(EconomyPoint(day, value) for day, value in sorted(values[item.id].items()))
        latest = next((p for p in reversed(points) if p.value is not None), None)
        stale = latest is not None and date.fromisoformat(latest.date) < now.date() - timedelta(
            days=7
        )
        result.append(
            replace(
                item,
                points=points,
                status="unavailable" if latest is None else "stale" if stale else "available",
                updated_at=now,
                source_updated_at=latest.date if latest else None,
                note=FX_NOTE
                + (
                    " The latest published observation is more than seven days old."
                    if stale
                    else ""
                ),
            )
        )
    return tuple(result)


def _rates(periods: list[Element], now: datetime) -> dict[str, dict[str, float | None]]:
    values: dict[str, dict[str, float | None]] = {code: {} for code in ("GBP", "USD", "CNY")}
    for period in periods:
        try:
            day = date.fromisoformat(period.attrib["time"])
        except ValueError:
            continue
        if not now.date() - timedelta(days=90) <= day <= now.date():
            continue
        if len(period) > 50:
            raise ValueError("Invalid exchange-rate currency count")
        for observations in values.values():
            if day.isoformat() in observations:
                raise ValueError("Duplicate exchange-rate date")
            observations[day.isoformat()] = None
        seen = set()
        for rate in period:
            code = rate.attrib.get("currency", "")
            if code not in values:
                continue
            if code in seen:
                raise ValueError("Duplicate exchange-rate currency")
            seen.add(code)
            try:
                value = float(rate.attrib.get("rate", ""))
            except ValueError:
                continue
            if math.isfinite(value) and 0 < value <= 1e9:
                values[code][day.isoformat()] = value
    if not any(any(v is not None for v in points.values()) for points in values.values()):
        raise ValueError("No recognised exchange-rate observations")
    return values

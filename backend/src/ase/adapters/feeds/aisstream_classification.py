"""Reported AIS ship types, never inferred from vessel names or MMSI prefixes."""

from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from typing import Any

from ase.domain.events import Event, content_hash, freeze_attributes

MAX_STATIC_RECORDS = 20_000
STATIC_TTL = timedelta(hours=6)


def static_record(data: dict[str, Any], now: datetime) -> tuple[str, datetime, int] | None:
    kind = data.get("MessageType")
    if kind not in ("ShipStaticData", "StaticDataReport"):
        return None
    try:
        metadata, report = data["MetaData"], data["Message"][kind]
        mmsi = metadata["MMSI"]
        if type(mmsi) is not int or not 1 <= mmsi <= 999_999_999:
            raise ValueError
        if report.get("UserID") != mmsi or report.get("Valid") is not True:
            raise ValueError
        raw_time = metadata["time_utc"]
        if not isinstance(raw_time, str) or len(raw_time) > 64:
            raise ValueError
        recorded = datetime.fromisoformat(raw_time.removesuffix(" UTC").replace(" +0000", "+00:00"))
        if recorded.tzinfo is None:
            raise ValueError
        recorded = recorded.astimezone(UTC)
        if not now - STATIC_TTL <= recorded <= now + timedelta(seconds=30):
            raise ValueError
        if kind == "StaticDataReport":
            report = report.get("ReportB", {})
            if report.get("Valid") is not True:
                raise ValueError
            ship_type = report.get("ShipType")
        else:
            ship_type = report.get("Type")
        if type(ship_type) is not int or not 1 <= ship_type <= 99:
            raise ValueError
        key = f"{mmsi:09d}"
        return key, recorded, ship_type
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
        return None


class VesselClassificationCache:
    def __init__(self) -> None:
        self._records: OrderedDict[str, tuple[datetime, int]] = OrderedDict()

    def observe(self, data: dict[str, Any], now: datetime) -> None:
        record = static_record(data, now)
        if record is None:
            return
        key, recorded, ship_type = record
        previous = self._records.get(key)
        if previous and recorded < previous[0]:
            return
        self._records.pop(key, None)
        self._records[key] = (recorded, ship_type)
        while len(self._records) > MAX_STATIC_RECORDS:
            self._records.popitem(last=False)

    def enrich(self, event: Event, now: datetime) -> Event:
        key = str(event.attributes.get("mmsi") or "")
        record = self._records.get(key)
        if record is None:
            return event
        recorded, ship_type = record
        if recorded < now - STATIC_TTL:
            self._records.pop(key, None)
            return event
        military = ship_type == 35
        attributes = freeze_attributes(
            {
                **event.attributes,
                "ship_type_code": ship_type,
                "ship_type_observed_at": recorded.isoformat(),
                "military": military,
                "ship_type_label": "Reported military operations"
                if military
                else "Reported law enforcement"
                if ship_type == 55
                else "Reported AIS ship type",
                "military_classification_basis": "reported_ais_ship_type_35" if military else None,
                "military_classification_observed_at": recorded.isoformat() if military else None,
            }
        )
        return event.with_changes(
            attributes=attributes,
            tags=event.tags | ({"military"} if military else set()),
            content_hash=content_hash(event.content_hash, str(ship_type), recorded.isoformat()),
        )

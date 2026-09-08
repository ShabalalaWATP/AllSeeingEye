"""Bounded provider classification shared across overlapping ADS-B queries."""

from collections import OrderedDict
from datetime import datetime, timedelta

from ase.domain.events import Event, content_hash, freeze_attributes

CLASSIFICATION_TTL = timedelta(hours=24)
MAX_CLASSIFICATIONS = 15_000


class AircraftClassificationCache:
    def __init__(self) -> None:
        self._military: OrderedDict[str, tuple[datetime, str]] = OrderedDict()

    def enrich(self, event: Event, now: datetime) -> Event:
        while self._military and next(iter(self._military.values()))[0] < now - CLASSIFICATION_TTL:
            self._military.popitem(last=False)
        if "military" in event.tags:
            basis = str(event.attributes.get("military_classification_basis") or "provider_label")
            self._military.pop(event.id, None)
            self._military[event.id] = (now, basis)
            while len(self._military) > MAX_CLASSIFICATIONS:
                self._military.popitem(last=False)
            return event
        classification = self._military.get(event.id)
        if classification is None:
            return event
        recorded, basis = classification
        attributes = freeze_attributes(
            {
                **event.attributes,
                "military": True,
                "military_classification_basis": basis,
                "military_classification_observed_at": recorded.isoformat(),
            }
        )
        return event.with_changes(
            tags=event.tags | {"military"},
            attributes=attributes,
            subtype="military_aircraft" if event.subtype == "aircraft" else event.subtype,
            content_hash=content_hash(event.content_hash, "military", recorded.isoformat()),
        )

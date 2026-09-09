"""Validate globally while retaining a geographically spread, bounded display sample."""

from heapq import heappush, heapreplace
from math import floor

from ase.domain.events import Event, content_hash, freeze_attributes

MAX_DISPLAY_OBSERVATIONS = 10_000
SAMPLING_METHOD = "Newest observation per 5-degree cell, then newest remaining detections"


class FirmsSelection:
    def __init__(self, limit: int = MAX_DISPLAY_OBSERVATIONS) -> None:
        if limit < 2_592:
            raise ValueError("Selection must accommodate all 5-degree cells")
        self.limit = limit
        self._order: dict[str, int] = {}
        self._latest: list[tuple[float, str]] = []
        self._kept: dict[str, Event] = {}
        self._cells: dict[tuple[int, int], Event] = {}

    @staticmethod
    def _key(event: Event) -> tuple[float, str]:
        if event.published_at is None:
            raise ValueError("FIRMS selection requires an acquisition time")
        return event.published_at.timestamp(), event.id

    def add(self, event: Event) -> None:
        if event.point is None:
            raise ValueError("FIRMS selection requires coordinates")
        key = self._key(event)
        cell = (
            min(71, floor((event.point.lon + 180) / 5)),
            min(35, floor((event.point.lat + 90) / 5)),
        )
        previous = self._cells.get(cell)
        if previous is None or key >= self._key(previous):
            self._cells[cell] = event
        if event.id in self._order:
            if event.id in self._kept:
                self._kept[event.id] = event
            return
        self._order[event.id] = len(self._order)
        if len(self._latest) < self.limit:
            heappush(self._latest, key)
            self._kept[event.id] = event
        elif key > self._latest[0]:
            _, removed = heapreplace(self._latest, key)
            del self._kept[removed]
            self._kept[event.id] = event

    def finish(self) -> list[Event]:
        total = len(self._order)
        sampled = total > self.limit
        if not sampled:
            selected = sorted(self._kept.values(), key=lambda event: self._order[event.id])
        else:
            chosen = {
                event.id: event
                for event in sorted(self._cells.values(), key=self._key, reverse=True)
            }
            for event in sorted(self._kept.values(), key=self._key, reverse=True):
                if len(chosen) >= self.limit:
                    break
                chosen.setdefault(event.id, event)
            selected = list(chosen.values())
        returned = len(selected)
        method = SAMPLING_METHOD if sampled else "All validated observations"
        self._cells.clear()
        self._kept.clear()
        self._latest.clear()
        self._order.clear()
        for index, event in enumerate(selected):
            attributes = dict(event.attributes)
            attributes.update(
                collection_total_observations=total,
                collection_returned_observations=returned,
                collection_sampling_method=method,
            )
            note = (
                f" Display sample: {returned:,} of {total:,} observations; "
                "5-degree cell representatives plus newest detections."
                if sampled
                else ""
            )
            selected[index] = event.with_changes(
                attributes=freeze_attributes(attributes),
                summary=(event.summary or "") + note,
                content_hash=content_hash(event.content_hash, str(total), str(returned), method),
            )
        return selected

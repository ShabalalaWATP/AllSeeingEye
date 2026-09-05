"""Response models for the maritime, space and cyber boards."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel

from ase.api.schemas_events import EventOut
from ase.application.trackers.modules import CyberBoard, MaritimeBoard, SpaceBoard, Tally
from ase.domain.events import Event


class TallyOut(BaseModel):
    key: str
    count: int
    max_severity: float | None

    @classmethod
    def from_tally(cls, row: Tally) -> Self:
        return cls(key=row.key, count=row.count, max_severity=row.max_severity)


def _events(events: tuple[Event, ...]) -> list[EventOut]:
    return [EventOut.from_event(event) for event in events]


def _tallies(rows: tuple[Tally, ...]) -> list[TallyOut]:
    return [TallyOut.from_tally(row) for row in rows]


class MaritimeBoardOut(BaseModel):
    warnings_total: int
    located: int
    by_area: list[TallyOut]
    by_kind: list[TallyOut]
    notable: list[EventOut]
    latest: list[EventOut]

    @classmethod
    def from_board(cls, board: MaritimeBoard) -> Self:
        return cls(
            warnings_total=board.warnings_total,
            located=board.located,
            by_area=_tallies(board.by_area),
            by_kind=_tallies(board.by_kind),
            notable=_events(board.notable),
            latest=_events(board.latest),
        )


class SpaceBoardOut(BaseModel):
    stations: list[EventOut]
    launches: list[EventOut]
    kp: float | None
    kp_level: str | None
    alerts_24h: int
    latest_alerts: list[EventOut]

    @classmethod
    def from_board(cls, board: SpaceBoard) -> Self:
        return cls(
            stations=_events(board.stations),
            launches=_events(board.launches),
            kp=board.kp,
            kp_level=board.kp_level,
            alerts_24h=board.alerts_24h,
            latest_alerts=_events(board.latest_alerts),
        )


class CyberBoardOut(BaseModel):
    outages_24h: int
    outages_by_country: list[TallyOut]
    ransomware_7d: int
    ransomware_by_country: list[TallyOut]
    ransomware_by_group: list[TallyOut]
    kev_7d: int
    latest_outages: list[EventOut]
    latest_claims: list[EventOut]
    latest_kev: list[EventOut]

    @classmethod
    def from_board(cls, board: CyberBoard) -> Self:
        return cls(
            outages_24h=board.outages_24h,
            outages_by_country=_tallies(board.outages_by_country),
            ransomware_7d=board.ransomware_7d,
            ransomware_by_country=_tallies(board.ransomware_by_country),
            ransomware_by_group=_tallies(board.ransomware_by_group),
            kev_7d=board.kev_7d,
            latest_outages=_events(board.latest_outages),
            latest_claims=_events(board.latest_claims),
            latest_kev=_events(board.latest_kev),
        )

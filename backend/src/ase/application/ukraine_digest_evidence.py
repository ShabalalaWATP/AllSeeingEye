"""The bounded evidence pack a Ukraine digest is written from, and nothing else.

Everything here comes from sources this application already collects. Items are trimmed,
dated and capped so one model call stays small and every claim can be traced back.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from ase.application.ukraine import ASSESSMENT_SOURCE, UkraineBoard, UpdateEntry
from ase.domain.events import Category, Event
from ase.domain.ukraine.confirmed import TOTAL_TYPE, CivilianHarm, ConfirmedLosses
from ase.domain.ukraine.control import ControlSnapshot
from ase.domain.ukraine.digest import MAX_EVIDENCE_ITEMS, MAX_SOURCE_IDS
from ase.domain.ukraine.lenses import Lens
from ase.domain.ukraine.losses import HEADLINE_CATEGORIES, LOSS_CATEGORIES, ClaimedLosses

MAX_LABEL = 180
MAX_DETAIL = 420
MAX_ASSESSMENTS = 6
MAX_BATTLEFIELD = 14
MAX_POLITICAL = 10
SIDE_LABELS = {"ru": "Russian", "ua": "Ukrainian"}


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """One dated, trimmed piece of the pack; ``id`` is what a digest change cites."""

    id: str
    kind: str
    source_id: str
    label: str
    detail: str
    dated_on: date | None
    url: str | None


@dataclass(frozen=True, slots=True)
class EvidencePack:
    period_start: date
    period_end: date
    items: tuple[EvidenceItem, ...]
    source_ids: tuple[str, ...]
    notes: tuple[str, ...]

    def by_id(self) -> dict[str, EvidenceItem]:
        return {item.id: item for item in self.items}

    def as_json(self) -> str:
        """What the model is shown: the period, the notes and the trimmed items."""
        return json.dumps(
            {
                "period": {
                    "from": self.period_start.isoformat(),
                    "to": self.period_end.isoformat(),
                },
                "notes": list(self.notes),
                "items": [
                    {
                        "id": item.id,
                        "kind": item.kind,
                        "source_id": item.source_id,
                        "date": item.dated_on.isoformat() if item.dated_on else None,
                        "label": item.label,
                        "detail": item.detail,
                    }
                    for item in self.items
                ],
            },
            ensure_ascii=False,
            allow_nan=False,
        )


def _trim(value: str | None, limit: int) -> str:
    text = " ".join((value or "").split())
    return text[:limit].rstrip()


def _dated(event: Event) -> date:
    return (event.published_at or event.observed_at).date()


def _is_political(entry: UpdateEntry) -> bool:
    return entry.event.category is Category.POLITICAL or Lens.DIPLOMACY in entry.lenses


class _Builder:
    def __init__(self, start: date, end: date) -> None:
        self._start, self._end = start, end
        self._items: list[EvidenceItem] = []
        self.notes: list[str] = []

    def add(
        self,
        kind: str,
        source_id: str,
        label: str,
        detail: str,
        dated_on: date | None,
        url: str | None,
    ) -> bool:
        if len(self._items) >= MAX_EVIDENCE_ITEMS or not label:
            return False
        self._items.append(
            EvidenceItem(
                id=f"e{len(self._items) + 1}",
                kind=kind,
                source_id=source_id,
                label=_trim(label, MAX_LABEL),
                detail=_trim(detail, MAX_DETAIL),
                dated_on=dated_on,
                url=url,
            )
        )
        return True

    def headlines(self, entries: list[UpdateEntry], kind: str, limit: int) -> None:
        taken = 0
        for entry in entries:
            if taken >= limit:
                return
            event = entry.event
            if self.add(
                kind,
                event.source_id,
                event.title_en or event.title,
                _trim(event.summary, MAX_DETAIL),
                _dated(event),
                event.url,
            ):
                taken += 1

    def pack(self) -> EvidencePack:
        sources = sorted({item.source_id for item in self._items})[:MAX_SOURCE_IDS]
        return EvidencePack(
            period_start=self._start,
            period_end=self._end,
            items=tuple(self._items),
            source_ids=tuple(sources),
            notes=tuple(self.notes),
        )


def _claim_detail(claim: ClaimedLosses) -> str:
    parts = [
        f"{LOSS_CATEGORIES[key]} {claim.totals[key]} claimed in total, {claim.increase.get(key, 0)}"
        f" claimed in the latest daily increase"
        for key in HEADLINE_CATEGORIES
        if key in claim.totals
    ]
    return "; ".join(parts)


def _add_claims(builder: _Builder, board: UkraineBoard, start: date) -> None:
    within = [claim for claim in board.claims if claim.reported_on >= start]
    if not within:
        builder.notes.append(
            "No General Staff of Ukraine daily claim was collected inside this fortnight."
        )
        return
    latest = within[-1]
    builder.add(
        "claim",
        "ukraine_general_staff",
        f"General Staff of Ukraine claimed Russian losses, day {latest.day}",
        f"These are one side's claims, not verified counts. {_claim_detail(latest)}.",
        latest.reported_on,
        latest.source_url,
    )


def _add_control(builder: _Builder, control: ControlSnapshot | None, start: date) -> None:
    if control is None:
        builder.notes.append(
            "No control map snapshot has been imported, so no territorial change is available."
        )
        return
    changed = [change for change in control.changes if start <= change.changed_on]
    if not changed:
        builder.notes.append(
            "The imported control map snapshot is assessed "
            f"{control.assessment_date.isoformat()} and records no settlement change inside "
            "this fortnight, so no territorial change is available."
        )
        return
    examples = "; ".join(
        f"{change.name} in {change.oblast} moved from {change.previous.value} to "
        f"{change.status.value} on {change.changed_on.isoformat()}"
        for change in changed[:5]
    )
    builder.add(
        "control",
        "viina_control",
        f"Reported control changed for {len(changed)} settlements in this fortnight",
        f"Reported control is a majority vote of public maps, not observed positions. {examples}.",
        control.assessment_date,
        control.source_url,
    )


def _add_losses(builder: _Builder, confirmed: ConfirmedLosses | None) -> None:
    if confirmed is None:
        builder.notes.append("No visually confirmed loss import is available.")
        return
    for side in ("ru", "ua"):
        row = next(
            (r for r in confirmed.rows if r.side.value == side and r.equipment_type == TOTAL_TYPE),
            None,
        )
        if row is None:
            continue
        builder.add(
            "losses",
            "oryx_losses",
            f"Visually confirmed {SIDE_LABELS[side]} equipment losses, all types",
            f"{row.total} recorded since February 2022, of which {row.destroyed} destroyed, "
            f"{row.damaged} damaged, {row.abandoned} abandoned and {row.captured} captured. "
            f"Recorded as of {confirmed.recorded_on.isoformat()}; a cumulative count of "
            "photographed losses, not a total of all losses.",
            confirmed.recorded_on,
            confirmed.source_url,
        )


def _add_civilian_harm(builder: _Builder, harm: CivilianHarm | None) -> None:
    latest = harm.latest if harm is not None else None
    if harm is None or latest is None:
        builder.notes.append("No United Nations civilian casualty import is available.")
        return
    builder.add(
        "civilian",
        "hrmmu_casualties",
        f"United Nations recorded civilian casualties for {latest.month.isoformat()[:7]}",
        f"{latest.killed} killed and {latest.injured} injured recorded in that calendar month. "
        "The United Nations states that actual figures are considerably higher.",
        latest.published_on or latest.month,
        latest.url,
    )


def evidence_pack(board: UkraineBoard, now: datetime) -> EvidencePack:
    """Build the bounded pack for the fortnight ending now, from the board already gathered."""
    end = now.date()
    start = end - timedelta(days=board.window_days)
    builder = _Builder(start, end)
    assessments = [
        entry
        for entry in board.updates
        if entry.event.source_id == ASSESSMENT_SOURCE and _dated(entry.event) >= start
    ]
    within = [
        entry
        for entry in board.updates
        if entry.event.source_id != ASSESSMENT_SOURCE and _dated(entry.event) >= start
    ]
    builder.headlines(assessments[:MAX_ASSESSMENTS], "assessment", MAX_ASSESSMENTS)
    builder.headlines(
        [entry for entry in within if not _is_political(entry)], "battlefield", MAX_BATTLEFIELD
    )
    builder.headlines(
        [entry for entry in within if _is_political(entry)], "political", MAX_POLITICAL
    )
    _add_claims(builder, board, start)
    _add_control(builder, board.control, start)
    _add_losses(builder, board.confirmed)
    _add_civilian_harm(builder, board.civilian_harm)
    if not assessments:
        builder.notes.append(
            "No Institute for the Study of War assessment was collected inside this fortnight."
        )
    return builder.pack()

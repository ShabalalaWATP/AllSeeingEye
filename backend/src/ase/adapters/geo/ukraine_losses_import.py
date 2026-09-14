"""Oryx visually confirmed losses through the leedrake5 daily CSV mirror (MIT), bounded.

One file per day holds both sides' counts by equipment type. The importer keeps the newest
day it can fetch as the table and the last month of totals as a series. Visual confirmation
undercounts by design; the page says so. Operator-run, never at runtime.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from ase.adapters.geo.bounded_download import DEFAULT_CONTACT, user_agent
from ase.domain.ukraine.confirmed import MAX_LOSS_ROWS, TOTAL_TYPE, loss_group

MIRROR = "https://raw.githubusercontent.com/leedrake5/Russia-Ukraine/main/data/byType/{day}.csv"
REPOSITORY = "https://github.com/leedrake5/Russia-Ukraine"
ORYX = "https://www.oryxspioenkop.com/2022/02/attack-on-europe-documenting-equipment.html"
MAX_FILE_BYTES = 200_000
LOOKBACK_DAYS = 7
SERIES_DAYS = 31
SIDES = {"Russia": "ru", "Ukraine": "ua"}
ATTRIBUTION = (
    "Oryx (Stijn Mitzer and Joost Oliemans), visually confirmed losses, read through the "
    "leedrake5/Russia-Ukraine daily CSV mirror (MIT)."
)


def _count(value: Any) -> int:
    try:
        return max(0, int(float(str(value).strip() or 0)))
    except ValueError:
        return 0


def parse_day(text: str) -> list[dict[str, Any]]:
    """Per-side rows for plain equipment types and the All Types total; summary lines dropped."""
    rows: list[dict[str, Any]] = []
    for record in csv.DictReader(io.StringIO(text)):
        side = SIDES.get((record.get("country") or "").strip())
        kind = " ".join((record.get("equipment_type") or "").split())
        if side is None or not kind or " - " in kind or "[" in kind:
            continue
        rows.append(
            {
                "side": side,
                "equipment_type": kind[:80],
                "group": "total" if kind == TOTAL_TYPE else loss_group(kind),
                "destroyed": _count(record.get("destroyed")),
                "damaged": _count(record.get("damaged")),
                "abandoned": _count(record.get("abandoned")),
                "captured": _count(record.get("captured")),
            }
        )
    if len(rows) > MAX_LOSS_ROWS:
        raise ValueError("Oryx day file holds more rows than the bound")
    return rows


def fetch_day(client: httpx.Client, day: date) -> str | None:
    response = client.get(MIRROR.format(day=day.isoformat()))
    if response.status_code == 404:
        return None
    response.raise_for_status()
    if len(response.content) > MAX_FILE_BYTES:
        raise ValueError("Oryx day file exceeds the byte bound")
    return response.text


def build_snapshot(client: httpx.Client, today: date, retrieved_at: datetime) -> dict[str, Any]:
    latest: tuple[date, list[dict[str, Any]]] | None = None
    days: list[dict[str, Any]] = []
    for offset in range(SERIES_DAYS):
        day = today - timedelta(days=offset)
        text = fetch_day(client, day)
        if text is None:
            if latest is None and offset >= LOOKBACK_DAYS:
                raise ValueError("No Oryx day file within the lookback window")
            continue
        rows = parse_day(text)
        if latest is None:
            latest = (day, rows)
        for row in rows:
            if row["group"] == "total":
                total = row["destroyed"] + row["damaged"] + row["abandoned"] + row["captured"]
                days.append({"on": day.isoformat(), "side": row["side"], "total": total})
    if latest is None:
        raise ValueError("No Oryx day file within the lookback window")
    days.sort(key=lambda item: (item["on"], item["side"]))
    return {
        "recorded_on": latest[0].isoformat(),
        "retrieved_at": retrieved_at.isoformat(timespec="seconds"),
        "attribution": ATTRIBUTION,
        "licence": "Mirror MIT; Oryx counts cited with attribution",
        "source_url": ORYX,
        "mirror_url": REPOSITORY,
        "rows": latest[1],
        "days": days,
    }


def import_ukraine_losses(destination: str, contact: str = DEFAULT_CONTACT) -> int:
    now = datetime.now(UTC)
    with httpx.Client(timeout=60, headers={"User-Agent": user_agent(contact)}) as client:
        snapshot = build_snapshot(client, now.date(), now)
    Path(destination).write_text(json.dumps(snapshot, separators=(",", ":")), encoding="utf-8")
    return len(snapshot["rows"])

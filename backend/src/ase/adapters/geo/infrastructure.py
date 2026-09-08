"""Packaged, attributed public map snapshots; never accept user filesystem paths."""

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


@lru_cache(maxsize=1)
def public_infrastructure() -> dict[str, Any]:
    root = files("ase.resources")
    return {
        "cables": json.loads(root.joinpath("submarine_cables.json").read_text(encoding="utf-8")),
        "ground_stations": json.loads(
            root.joinpath("ground_stations.json").read_text(encoding="utf-8")
        ),
        "snapshot_date": "2026-09-08",
        "cable_attribution": (
            "© OpenStreetMap contributors. Approximate mapped cable segments; coverage incomplete."
        ),
        "cable_licence_url": "https://www.openstreetmap.org/copyright",
    }

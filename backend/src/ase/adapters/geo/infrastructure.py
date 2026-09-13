"""Packaged, attributed public map snapshots; never accept user filesystem paths."""

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


@lru_cache(maxsize=1)
def public_infrastructure() -> dict[str, Any]:
    root = files("ase.resources")
    nuclear = json.loads(root.joinpath("nuclear_facilities.json").read_text(encoding="utf-8"))
    centres = json.loads(root.joinpath("data_centres.json").read_text(encoding="utf-8"))
    energy = json.loads(root.joinpath("energy_sites.json").read_text(encoding="utf-8"))
    chips = json.loads(root.joinpath("semiconductor_sites.json").read_text(encoding="utf-8"))
    return {
        **nuclear,
        "data_centres": centres["items"],
        "data_centre_attribution": centres["attribution"],
        "data_centre_licence_url": centres["licence_url"],
        "data_centre_snapshot_date": centres["snapshot_date"],
        "energy_sites": energy["items"],
        "semiconductor_sites": chips["items"],
        "site_attribution": energy["attribution"],
        "site_licence_url": energy["licence_url"],
        "site_snapshot_date": energy["snapshot_date"],
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

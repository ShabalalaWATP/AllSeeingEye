"""Data the app uses outside the feed scheduler and research registry, described honestly.

Camera indexes, map layers, Ukraine tracker datasets and reference imports are not event
sources, so they carry no reliability grade. Each asset says who publishes it, how the app
obtains it, which licence applies and whether it is usable on this server now. Nothing here
fetches upstream data or reads credential values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ase.application.source_inventory import ConnectionState, SourceRequirement

AssetFamily = Literal["camera_index", "map_layer", "ukraine_dataset", "reference_dataset"]
AssetDelivery = Literal[
    "official_index",
    "curated_catalogue",
    "third_party_directory",
    "bundled_snapshot",
    "request_service",
    "browser_direct",
]
ASSET_FAMILIES: tuple[AssetFamily, ...] = (
    "camera_index",
    "map_layer",
    "ukraine_dataset",
    "reference_dataset",
)


@dataclass(frozen=True, slots=True)
class SourceAsset:
    id: str
    name: str
    family: AssetFamily
    delivery: AssetDelivery
    organisation: str
    description: str
    licence_note: str
    homepage: str | None
    coverage_note: str
    refresh_note: str
    state: ConnectionState
    detail: str
    requirement: SourceRequirement | None = None
    as_of: str | None = None
    records: int | None = None


_DELIVERY_DETAILS: dict[AssetDelivery, str] = {
    "official_index": "Loads from the publisher's index when the map asks for it.",
    "curated_catalogue": "Packaged catalogue served from the application; no upstream request.",
    "third_party_directory": "Loads from a third-party directory when the map asks for it.",
    "bundled_snapshot": "Packaged snapshot served from the application; no upstream request.",
    "request_service": "Queried by the server only when you use the tool that needs it.",
    "browser_direct": "Loaded by your browser directly from the provider.",
}


def delivery_detail(delivery: AssetDelivery) -> str:
    return _DELIVERY_DETAILS[delivery]


def snapshot_state(present: bool, command: str) -> tuple[ConnectionState, str]:
    """A packaged snapshot is available, or names the import command that recreates it."""
    if present:
        return ConnectionState.AVAILABLE, delivery_detail("bundled_snapshot")
    return ConnectionState.NOT_CONFIGURED, f"The packaged snapshot is missing; run {command}."

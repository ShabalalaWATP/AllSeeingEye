"""Strict versioned map state conversion and reproducible revision byte accounting."""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from typing import Any

from ase.domain.map_geometry import parse_map_geometry
from ase.domain.map_topology import TopologyBudget
from ase.domain.map_views import MAX_VIEW_BYTES, MapCamera, MapOverlay, MapViewState


def state_to_dict(state: MapViewState) -> dict[str, Any]:
    return {
        "schema_version": state.schema_version,
        "display_transform": state.display_transform,
        "camera": asdict(state.camera),
        "projection": state.projection,
        "basemap": state.basemap,
        "source_ids": list(state.source_ids),
        "published_since": (
            state.published_since.astimezone(UTC).isoformat() if state.published_since else None
        ),
        "include_unknown_dates": state.include_unknown_dates,
        "published_until": (
            state.published_until.astimezone(UTC).isoformat() if state.published_until else None
        ),
        "selected_evidence": state.selected_evidence,
        "overlays": [
            {
                "geometry": overlay.geometry.to_collection(),
                "source": overlay.source,
                "dataset_date": overlay.dataset_date.isoformat(),
                "attribution": overlay.attribution,
                "precision": overlay.precision,
                "visible": overlay.visible,
            }
            for overlay in state.overlays
        ],
        "aoi": state.aoi.to_collection() if state.aoi else None,
    }


def canonical_state(state: MapViewState) -> str:
    encoded = json.dumps(
        state_to_dict(state),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    if len(encoded.encode("utf-8")) > MAX_VIEW_BYTES:
        raise ValueError("Map state exceeds its byte budget")
    return encoded


def revision_bytes(state: MapViewState, title: str) -> int:
    """Charge canonical state, title and a fixed metadata allowance to storage quotas."""
    return len(canonical_state(state).encode("utf-8")) + len(title.encode("utf-8")) + 1024


def revision_digest(state: MapViewState, title: str, version_id: str, evidence_hash: str) -> str:
    content = json.dumps(
        {
            "state": state_to_dict(state),
            "title": title,
            "report_version_id": version_id,
            "evidence_sha256": evidence_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _fields(value: object, names: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != names:
        raise ValueError("Invalid map state fields")
    return value


def state_from_dict(raw: object) -> MapViewState:
    """Validate transport and stored state; never trust a client-computed hash."""
    data = _fields(
        raw,
        {
            "schema_version",
            "display_transform",
            "camera",
            "projection",
            "basemap",
            "source_ids",
            "published_since",
            "published_until",
            "include_unknown_dates",
            "selected_evidence",
            "overlays",
            "aoi",
        },
    )
    # Bound before geometry normalisation or copying into durable state.
    try:
        encoded = json.dumps(data, ensure_ascii=False, allow_nan=False)
    except (RecursionError, TypeError, OverflowError) as exc:
        raise ValueError("Invalid map state JSON") from exc
    if len(encoded.encode("utf-8")) > MAX_VIEW_BYTES:
        raise ValueError("Map state exceeds its byte budget")
    camera = _fields(data["camera"], {"longitude", "latitude", "zoom", "bearing", "pitch"})
    if not isinstance(data["source_ids"], list) or not isinstance(data["overlays"], list):
        raise ValueError("Invalid map state arrays")
    if len(data["overlays"]) > 8:
        raise ValueError("Map views allow at most eight overlays")
    overlays = []
    topology = TopologyBudget()
    for raw_overlay in data["overlays"]:
        overlay = _fields(
            raw_overlay,
            {
                "geometry",
                "source",
                "dataset_date",
                "attribution",
                "precision",
                "visible",
            },
        )
        if not isinstance(overlay["dataset_date"], str):
            raise ValueError("Invalid map dataset date")
        overlays.append(
            MapOverlay(
                parse_map_geometry(
                    json.dumps(overlay["geometry"], ensure_ascii=False), topology=topology
                ),
                overlay["source"],
                date.fromisoformat(overlay["dataset_date"]),
                overlay["attribution"],
                overlay["precision"],
                overlay["visible"],
            )
        )
    cutoff = data["published_since"]
    until = data["published_until"]
    if any(item is not None and not isinstance(item, str) for item in (cutoff, until)):
        raise ValueError("Invalid map publication cutoff")
    state = MapViewState(
        camera=MapCamera(**camera),
        projection=data["projection"],
        basemap=data["basemap"],
        source_ids=tuple(data["source_ids"]),
        published_since=datetime.fromisoformat(cutoff) if cutoff is not None else None,
        published_until=datetime.fromisoformat(until) if until is not None else None,
        include_unknown_dates=data["include_unknown_dates"],
        selected_evidence=data["selected_evidence"],
        overlays=tuple(overlays),
        aoi=parse_map_geometry(json.dumps(data["aoi"], ensure_ascii=False), topology=topology)
        if data["aoi"] is not None
        else None,
        schema_version=data["schema_version"],
        display_transform=data["display_transform"],
    )
    canonical_state(state)
    return state

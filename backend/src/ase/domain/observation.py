"""Observation times and catalogue identity, distinct from publication and retrieval."""

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ObservationMetadata:
    acquired_at: datetime
    collection_id: str
    item_id: str
    limitations: str
    processed_at: datetime | None = None
    scene_cloud_cover: float | None = None

    def __post_init__(self) -> None:
        for timestamp in (self.acquired_at, self.processed_at):
            if timestamp is not None and (
                not isinstance(timestamp, datetime) or timestamp.utcoffset() is None
            ):
                raise ValueError("Observation dates must include a timezone")
        if self.acquired_at is None:
            raise ValueError("Observation acquisition time is required")
        for value, limit in (
            (self.collection_id, 300),
            (self.item_id, 300),
            (self.limitations, 2000),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError("Observation identity/limitations are missing or oversized")
            value.encode("utf-8")
        cloud = self.scene_cloud_cover
        if cloud is not None and (
            type(cloud) not in (int, float) or not 0 <= cloud <= 100 or not math.isfinite(cloud)
        ):
            raise ValueError("Scene cloud cover must be a finite percentage")


def observation_to_dict(value: ObservationMetadata) -> dict[str, Any]:
    return {
        "acquired_at": value.acquired_at.isoformat(),
        "processed_at": value.processed_at.isoformat() if value.processed_at else None,
        "collection_id": value.collection_id,
        "item_id": value.item_id,
        "limitations": value.limitations,
        "scene_cloud_cover": value.scene_cloud_cover,
    }


def observation_from_dict(value: Any) -> ObservationMetadata | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {
        "acquired_at",
        "processed_at",
        "collection_id",
        "item_id",
        "limitations",
        "scene_cloud_cover",
    }:
        raise ValueError("Invalid frozen observation metadata")
    try:
        return ObservationMetadata(
            acquired_at=datetime.fromisoformat(value["acquired_at"]),
            processed_at=datetime.fromisoformat(value["processed_at"])
            if value["processed_at"] is not None
            else None,
            collection_id=value["collection_id"],
            item_id=value["item_id"],
            limitations=value["limitations"],
            scene_cloud_cover=value["scene_cloud_cover"],
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid frozen observation metadata") from exc

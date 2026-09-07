"""Bounded client-rendered map image export inputs and rendering port."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from ase.domain.map_views import MapView, MapViewRevision

MAX_MAP_IMAGE_BYTES = 8 * 1024 * 1024
MAX_MAP_IMAGE_BODY = 12 * 1024 * 1024
MAX_MAP_PACKAGE_BYTES = 16 * 1024 * 1024


@dataclass(frozen=True)
class MapImageOptions:
    png_base64: str
    include_annotations: bool = False
    use_basis: Literal["standard", "noncommercial", "licensed"] = "standard"
    permitted_use: str = ""


class MapImageRenderer(Protocol):
    def render(
        self,
        view: MapView,
        revision: MapViewRevision,
        options: MapImageOptions,
        received_at: datetime,
    ) -> bytes: ...

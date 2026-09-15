"""Assembles camera, map, Ukraine and reference assets without network calls or secrets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ase.application.source_assets import SourceAsset
from ase.container.source_asset_cameras import camera_assets
from ase.container.source_asset_datasets import reference_assets, ukraine_assets
from ase.container.source_asset_maps import map_layer_assets
from ase.domain.users import User

if TYPE_CHECKING:
    from ase.container import Container


def build_source_assets(container: Container, user: User) -> list[SourceAsset]:
    code = container.settings.wsdot_access_code
    wsdot = code is not None and bool(code.get_secret_value().strip())
    return [
        *camera_assets(container.cameras, user, wsdot),
        *map_layer_assets(),
        *ukraine_assets(container),
        *reference_assets(container),
    ]

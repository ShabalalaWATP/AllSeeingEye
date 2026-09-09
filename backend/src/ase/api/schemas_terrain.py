"""Fixed-resolution, aligned public DEM sample contract."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from ase.domain.terrain import MAX_TERRAIN_POSITIONS, MERCATOR_LIMIT


class TerrainPositionIn(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, strict=True)
    lat: float = Field(ge=-MERCATOR_LIMIT, le=MERCATOR_LIMIT, strict=True)


class TerrainElevationsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    positions: list[TerrainPositionIn] = Field(min_length=1, max_length=MAX_TERRAIN_POSITIONS)


class TerrainElevationsOut(BaseModel):
    elevations_m: list[Annotated[float, Field(ge=-12000, le=10000)]] = Field(
        min_length=1, max_length=MAX_TERRAIN_POSITIONS
    )
    zoom: Literal[10] = 10
    resolution_m: float = Field(gt=0, le=153)
    provider: Literal["Mapzen Terrain Tiles"] = "Mapzen Terrain Tiles"
    attribution: str = (
        "Mapzen Terrain Tiles. ArcticDEM: DigitalGlobe imagery, NSF awards 1043681, 1559691, "
        "1542736. Australia: © Commonwealth of Australia (Geoscience Australia) 2017. "
        "Austria: © offene Daten Österreichs, Digitales Geländemodell (DGM) Österreich. "
        "Canada: contains information licensed under the Open Government Licence, Canada. "
        "Europe: produced using Copernicus data and information funded by the European Union, "
        "EU-DEM layers. ETOPO1: U.S. National Oceanic and Atmospheric Administration. "
        "Mexico: INEGI, Continental relief, 2016. New Zealand: Copyright 2011 Crown copyright, "
        "Land Information New Zealand and the New Zealand Government, all rights reserved. "
        "Norway: © Kartverket. United Kingdom: © Environment Agency copyright and/or database "
        "right 2015, all rights reserved. 3DEP, GMTED2010 and SRTM: U.S. Geological Survey."
    )
    attribution_url: str = "https://github.com/tilezen/joerd/blob/master/docs/attribution.md"
    limitations: str = (
        "Nearest-pixel source elevations in metres, including negative terrain/bathymetry; "
        "not ellipsoid or water-surface heights. Nominal pixel spacing is not source accuracy. "
        "Historical mixed-resolution terrain can miss buildings, vegetation and small obstacles. "
        "No survey-grade vertical datum or current ground conditions are guaranteed."
    )

"""Explicit HF smooth-earth model input limits and reference definitions."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GroundwaveIn(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    frequency_mhz: float = Field(ge=1.6, le=30)
    tx_power_w: float = Field(ge=0.001, le=100000)
    tx_height_m: float = Field(
        ge=0, le=50, description="Antenna height above local ground, not sea level."
    )
    rx_height_m: float = Field(
        ge=0, le=50, description="Antenna height above local ground, not sea level."
    )
    conductivity_sm: float = Field(ge=0.00001, le=10)
    relative_permittivity: float = Field(ge=1, le=100)
    surface_refractivity: float = Field(default=301, ge=250, le=400)
    tx_gain_dbi: float = Field(default=0, ge=-30, le=30)
    rx_gain_dbi: float = Field(default=0, ge=-30, le=30)
    system_loss_db: float = Field(default=0, ge=0, le=120)
    max_distance_km: float = Field(default=200, ge=2, le=200)
    sample_count: int = Field(default=48, ge=2, le=64, strict=True)


class GroundwaveSampleOut(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, from_attributes=True)
    distance_km: float
    basic_transmission_loss_db: float
    native_reference_field_dbuv_m: float
    received_power_dbm: float
    method: Literal["flat_earth", "residue_series"]


class GroundwaveOut(BaseModel):
    status: Literal["calculated"] = "calculated"
    model: Literal["NTIA LFMF 1.1 (P.368-10)"] = "NTIA LFMF 1.1 (P.368-10)"
    samples: list[GroundwaveSampleOut] = Field(min_length=2, max_length=64)
    source_url: str = "https://github.com/NTIA/LFMF/tree/v1.1"
    limitations: str = (
        "Vertical polarisation over homogeneous smooth Earth, 1.6 to 30 MHz, 0 to 50 m antenna "
        "heights above ground. Samples begin at 1 km and end at the requested distance, "
        "at most 200 km. Does not model irregular terrain, buildings, vegetation, mixed "
        "land/sea paths, skywave or changing ground conditions. Native reference field "
        "uses specified antenna-input power and the model's 4.77 dBi transmitting antenna, "
        "without user gains/losses. Received power applies user gains and combined system "
        "loss to native basic transmission loss. A sensitivity crossing is an assumed "
        "homogeneous-ground contour, not a measured or guaranteed service boundary."
    )

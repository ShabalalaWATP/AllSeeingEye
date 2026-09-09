"""Inputs and results for a homogeneous smooth-earth HF groundwave study."""

from dataclasses import dataclass
from math import isfinite
from typing import Literal


@dataclass(frozen=True)
class GroundwaveInput:
    frequency_mhz: float
    tx_power_w: float
    tx_height_m: float
    rx_height_m: float
    conductivity_sm: float
    relative_permittivity: float
    surface_refractivity: float = 301
    tx_gain_dbi: float = 0
    rx_gain_dbi: float = 0
    system_loss_db: float = 0
    max_distance_km: float = 200
    sample_count: int = 48

    def __post_init__(self) -> None:
        bounds = (
            (self.frequency_mhz, 1.6, 30),
            (self.tx_power_w, 0.001, 100000),
            (self.tx_height_m, 0, 50),
            (self.rx_height_m, 0, 50),
            (self.conductivity_sm, 0.00001, 10),
            (self.relative_permittivity, 1, 100),
            (self.surface_refractivity, 250, 400),
            (self.tx_gain_dbi, -30, 30),
            (self.rx_gain_dbi, -30, 30),
            (self.system_loss_db, 0, 120),
            (self.max_distance_km, 2, 200),
        )
        if any(not isfinite(value) or not low <= value <= high for value, low, high in bounds):
            raise ValueError("Groundwave inputs exceed the supported study bounds.")
        if type(self.sample_count) is not int or not 2 <= self.sample_count <= 64:
            raise ValueError("Use between 2 and 64 groundwave samples.")


@dataclass(frozen=True)
class GroundwaveSample:
    distance_km: float
    basic_transmission_loss_db: float
    native_reference_field_dbuv_m: float
    received_power_dbm: float
    method: Literal["flat_earth", "residue_series"]

"""Fixed NASA VIIRS products currently recommended for continuing collection."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FirmsSensor:
    suffix: str
    name: str
    product: str
    satellite_codes: frozenset[str]
    public_path: str


NOAA20 = FirmsSensor(
    "noaa20",
    "NOAA-20",
    "VIIRS_NOAA20_NRT",
    frozenset({"N20", "1"}),
    "/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv",
)
NOAA21 = FirmsSensor(
    "noaa21",
    "NOAA-21",
    "VIIRS_NOAA21_NRT",
    frozenset({"N21", "2"}),
    "/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_Global_24h.csv",
)
FIRMS_SENSORS = (NOAA20, NOAA21)


def require_sensor(sensor: FirmsSensor) -> FirmsSensor:
    if sensor not in FIRMS_SENSORS:
        raise ValueError("Unsupported FIRMS sensor")
    return sensor

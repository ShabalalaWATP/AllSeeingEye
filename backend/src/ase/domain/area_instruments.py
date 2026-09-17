"""Bounded readings from the instruments this application already collects, inside one scope.

An instrument reading counts records that a live feed placed inside the resolved scope
during its own retention window. It is not a survey and never a claim of absence:
coverage is partial, retention is short, and a record is a detection, not an event with
a cause. Readings are only taken when the question asks for them or the operator drew
the area, so an ordinary question never carries map data it did not want.
"""

from __future__ import annotations

from dataclasses import dataclass

INSTRUMENT_POLICY_VERSION = "ase-area-instruments-v1"
MAX_INSTRUMENT_READINGS = 4
MAX_INSTRUMENT_EXAMPLES = 3

NO_INSTRUMENTS = (
    "No spatial instrument was read for this report. Either the question named none of the "
    "reviewed physical effects and the scope was not drawn by the operator, or no instrument "
    "holds a record inside the scope. Nothing here says the scope was quiet."
)
INSTRUMENT_CAVEAT = (
    "Each count covers only what the live store still holds, which is a short rolling window "
    "and never a complete record. Coverage is uneven, a detection is not an incident, and an "
    "empty count is not clearance."
)


@dataclass(frozen=True, slots=True)
class InstrumentReading:
    """One instrument's count inside the scope, with the window and the limits it carries."""

    instrument: str
    label: str
    inside: int
    considered: int
    window_hours: int
    basis: str
    examples: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.instrument or not self.label or not self.basis:
            raise ValueError("An instrument reading needs its class, label and basis")
        if self.inside < 0 or self.considered < self.inside or self.window_hours <= 0:
            raise ValueError("An instrument reading counts inside a positive window")
        if len(self.examples) > MAX_INSTRUMENT_EXAMPLES or any(
            not row or len(row) > 200 for row in self.examples
        ):
            raise ValueError("Instrument examples are few and bounded")
        if len(self.label) > 120 or len(self.basis) > 600:
            raise ValueError("Instrument labels and bases are bounded")

    def describe(self) -> str:
        named = "; ".join(self.examples)
        listed = f" Examples: {named}." if named else ""
        return (
            f"{self.label}: {self.inside} record(s) inside the scope, from "
            f"{self.considered} held for the last {self.window_hours} hour(s)."
            f"{listed} {self.basis}"
        )


def bound_readings(readings: tuple[InstrumentReading, ...]) -> tuple[InstrumentReading, ...]:
    """Instrument order is stable; a reading with nothing inside the scope is still honest."""
    if len(readings) > MAX_INSTRUMENT_READINGS:
        raise ValueError("More instrument readings than the reviewed bound allows")
    return readings


def readings_to_list(readings: tuple[InstrumentReading, ...]) -> list[dict[str, object]]:
    return [
        {
            "instrument": row.instrument,
            "label": row.label,
            "inside": row.inside,
            "considered": row.considered,
            "window_hours": row.window_hours,
            "basis": row.basis,
            "examples": list(row.examples),
        }
        for row in readings
    ]


def readings_from_list(rows: list[object]) -> tuple[InstrumentReading, ...]:
    if len(rows) > MAX_INSTRUMENT_READINGS:
        raise ValueError("Invalid frozen instrument readings")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Frozen instrument readings must be objects")
        examples = row.get("examples", [])
        if not isinstance(examples, list | tuple):
            raise ValueError("Frozen instrument examples must be a list")
        try:
            result.append(
                InstrumentReading(
                    str(row["instrument"]),
                    str(row["label"]),
                    int(row["inside"]),
                    int(row["considered"]),
                    int(row["window_hours"]),
                    str(row["basis"]),
                    tuple(str(value) for value in examples),
                )
            )
        except (KeyError, TypeError) as exc:
            raise ValueError("Malformed frozen instrument reading") from exc
    return tuple(result)

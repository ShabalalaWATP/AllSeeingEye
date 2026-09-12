"""The supported economic reporting windows, separate from refresh frequency."""

from enum import IntEnum


class EconomyWindowDays(IntEnum):
    TWO = 2
    FIVE = 5
    SEVEN = 7
    FOURTEEN = 14


def economy_window(value: int) -> EconomyWindowDays:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("Choose a 2, 5, 7 or 14 day economic summary")
    return EconomyWindowDays(value)

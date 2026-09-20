"""Bounded team names and descriptions shared by team management operations."""

from ase.domain.errors import InvalidRequest


def team_name(value: str) -> str:
    result = value.strip()
    if not result or len(result) > 120 or any(ord(char) < 32 for char in result):
        raise InvalidRequest("Team names must contain 1 to 120 printable characters.")
    return result


def team_description(value: str | None) -> str | None:
    if value is None:
        return None
    result = value.strip()
    if len(result) > 500 or any(ord(char) < 32 for char in result):
        raise InvalidRequest("Team descriptions must contain at most 500 printable characters.")
    return result or None

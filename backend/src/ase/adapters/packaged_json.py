"""Strict readers for the reviewed JSON catalogues packaged under ``ase.resources``.

A packaged catalogue is reviewed data, not upstream input, so a shape its loader does not
expect is a packaging fault. It fails with the file, record and field named instead of
being skipped, coerced or defaulted. Duplicate object keys are refused too, because
``json`` would otherwise keep the last one silently.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Collection
from importlib import resources
from typing import Any, Final
from urllib.parse import urlsplit

PACKAGE: Final = "ase.resources"
MAX_TEXT: Final = 2048
NAME = re.compile(r"[a-z][a-z0-9_]{0,63}")
LANGUAGE = re.compile(r"[a-z]{2,3}")


class CatalogueError(ValueError):
    """A packaged catalogue does not have the shape its loader reviewed."""


def parse(where: str, raw: str) -> Any:
    """Decode one catalogue, refusing invalid JSON and repeated object keys."""

    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise CatalogueError(f"{where}: duplicate key {key!r}")
            result[key] = value
        return result

    try:
        return json.loads(raw, object_pairs_hook=unique_keys)
    except json.JSONDecodeError as error:
        raise CatalogueError(f"{where}: not valid JSON ({error.msg})") from error


def load_resource(folder: str, file_name: str) -> Any:
    """Parse one packaged file; only fixed folder and file names reach this call."""
    resource = resources.files(PACKAGE).joinpath(folder).joinpath(file_name)
    return parse(f"{folder}/{file_name}", resource.read_text(encoding="utf-8"))


def fields(
    where: str,
    value: object,
    required: Collection[str],
    optional: Collection[str] = (),
) -> dict[str, Any]:
    """An object carrying every required key and nothing unreviewed."""
    if not isinstance(value, dict):
        raise CatalogueError(f"{where}: expected an object")
    keys = set(value)
    if missing := set(required) - keys:
        raise CatalogueError(f"{where}: missing {', '.join(sorted(missing))}")
    if unknown := keys - set(required) - set(optional):
        raise CatalogueError(f"{where}: unknown field(s) {', '.join(sorted(unknown))}")
    return value


def records(where: str, value: object, limit: int) -> list[Any]:
    if not isinstance(value, list) or not value or len(value) > limit:
        raise CatalogueError(f"{where}: expected a list of 1 to {limit} entries")
    return value


def text(where: str, value: object, *, empty: bool = False, limit: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or len(value) > limit or (not value and not empty):
        raise CatalogueError(f"{where}: expected {'' if empty else 'non-empty '}text")
    if value != value.strip() or any(ord(char) < 32 for char in value):
        raise CatalogueError(f"{where}: text has surrounding space or control characters")
    return value


def lines(where: str, value: object) -> tuple[str, ...]:
    """A provenance note kept as wrapped lines; blank lines separate paragraphs."""
    rows = records(where, value, 64)
    return tuple(text(f"{where}[{index}]", row, empty=True) for index, row in enumerate(rows))


def name(where: str, value: object) -> str:
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise CatalogueError(f"{where}: expected a lower-case name")
    return value


def language(where: str, value: object) -> str:
    """A lower-case ISO 639 language code as the source declares it."""
    if not isinstance(value, str) or not LANGUAGE.fullmatch(value):
        raise CatalogueError(f"{where}: expected a lower-case language code")
    return value


def names(where: str, value: object, *, empty: bool = False) -> tuple[str, ...]:
    """Unique lower-case names in their packaged order."""
    if not isinstance(value, list) or (not value and not empty) or len(value) > 32:
        raise CatalogueError(f"{where}: expected a list of names")
    result = tuple(name(f"{where}[{index}]", row) for index, row in enumerate(value))
    if len(set(result)) != len(result):
        raise CatalogueError(f"{where}: a name is listed twice")
    return result


def choice(where: str, value: object, allowed: Collection[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise CatalogueError(f"{where}: expected one of {', '.join(sorted(allowed))}")
    return value


def integer(where: str, value: object, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise CatalogueError(f"{where}: expected a whole number from {low} to {high}")
    return value


def number(where: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise CatalogueError(f"{where}: expected a finite number")
    return value


def flag(where: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise CatalogueError(f"{where}: expected true or false")
    return value


def https_url(where: str, value: object) -> str:
    url = text(where, value)
    if not url.startswith("https://") or any(char.isspace() for char in url):
        raise CatalogueError(f"{where}: expected an HTTPS URL")
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
    except ValueError as exc:
        raise CatalogueError(f"{where}: expected an HTTPS URL") from exc
    # Credentials in the authority can disguise the real host from a reviewer.
    if not hostname or "@" in parts.netloc:
        raise CatalogueError(f"{where}: expected an HTTPS URL with a plain host")
    return url


def unique(where: str, values: Collection[str]) -> None:
    if len(set(values)) != len(values):
        raise CatalogueError(f"{where}: an identifier is listed twice")

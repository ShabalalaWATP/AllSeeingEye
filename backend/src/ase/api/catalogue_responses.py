"""Bounded immutable catalogue representations with authenticated revalidation.

Catalogue providers replace their snapshot on refresh. Identity is its version
boundary; a representation retains the snapshot so object IDs cannot be reused.
Weak validators intentionally remain valid when the proxy applies compression.
"""

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Response
from pydantic import BaseModel

CATALOGUE_PATHS = frozenset({"/api/map-infrastructure", "/api/countries"})
_VALIDATORS = re.compile(r'(?:W/)?"[\x21\x23-\x7e\x80-\xff]*"')
_VALIDATOR_LIST = re.compile(
    r"\s*" + _VALIDATORS.pattern + r"(?:\s*,\s*" + _VALIDATORS.pattern + r")*\s*"
)


@dataclass(frozen=True)
class Representation:
    body: bytes
    etag: str

    def response(self, condition: str | None) -> Response:
        headers = {
            "Cache-Control": "private, no-cache",
            "ETag": self.etag,
            "Vary": "Accept-Encoding",
        }
        validators = (
            _VALIDATORS.findall(condition)
            if condition and _VALIDATOR_LIST.fullmatch(condition)
            else []
        )
        matches = (condition or "").strip() == "*" or any(
            value.removeprefix("W/") == self.etag.removeprefix("W/") for value in validators
        )
        return Response(
            content=b"" if matches else self.body,
            status_code=304 if matches else 200,
            media_type=None if matches else "application/json",
            headers=headers,
        )


class CatalogueResponses:
    def __init__(self) -> None:
        self._snapshots: dict[str, tuple[object, Representation]] = {}

    def get(self, name: str, snapshot: object, build: Callable[[], BaseModel]) -> Representation:
        current = self._snapshots.get(name)
        if current is not None and current[0] is snapshot:
            return current[1]
        body = build().model_dump_json().encode("utf-8")
        result = Representation(body, f'W/"{hashlib.sha256(body).hexdigest()}"')
        # Exactly two reviewed routes, each with one replace-in-place snapshot.
        if name not in CATALOGUE_PATHS:
            raise ValueError("Unknown catalogue representation")
        self._snapshots[name] = (snapshot, result)
        return result


catalogue_responses = CatalogueResponses()

"""Packaged reference catalogue and its cached images, validated once at load."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from functools import lru_cache
from importlib.resources import files
from typing import Any

from ase.domain.ukraine.reference import (
    MAX_IMAGE_BYTES,
    MAX_LINKS,
    MAX_TEXT,
    MAX_TITLE,
    EquipmentEntry,
    ForceNode,
    Link,
    ReferenceCatalogue,
    ReferenceImage,
    Side,
    TimelineEvent,
    TimelinePhase,
)

RESOURCE = "ukraine_reference.json"
IMAGE_FOLDER = "ukraine_images"
IMAGE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,59}$")


def _text(value: Any, limit: int = MAX_TITLE) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Reference text field missing or too long")
    return value.strip()


def _optional(value: Any, limit: int = MAX_TEXT) -> str | None:
    return None if value is None else _text(value, limit)


def _qid(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"Q\d{1,12}", value):
        raise ValueError("Reference Wikidata id malformed")
    return value


def _image_id(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not IMAGE_ID.fullmatch(value):
        raise ValueError("Reference image id malformed")
    return value


def _links(value: Any) -> tuple[Link, ...]:
    if not isinstance(value, list) or len(value) > MAX_LINKS:
        raise ValueError("Reference links malformed")
    links: list[Link] = []
    for item in value:
        url = _text(item.get("url"), 600)
        if not url.startswith("https://"):
            raise ValueError("Reference links must be https")
        links.append(Link(label=_text(item.get("label"), 120), url=url))
    return tuple(links)


def _date(value: Any) -> date:
    return date.fromisoformat(_text(value, 10))


def parse_catalogue(raw: dict[str, Any]) -> ReferenceCatalogue:
    images = {
        _text(key, 60): ReferenceImage(
            id=_text(key, 60),
            licence=_text(item.get("licence"), 80),
            credit=_text(item.get("credit"), 300),
            source_url=_text(item.get("source_url"), 600),
            width=int(item.get("width") or 0),
            height=int(item.get("height") or 0),
            bytes=int(item.get("bytes") or 0),
        )
        for key, item in (raw.get("images") or {}).items()
    }
    if any(image.bytes > MAX_IMAGE_BYTES for image in images.values()):
        raise ValueError("Reference image exceeds the byte bound")
    return ReferenceCatalogue(
        retrieved_at=datetime.fromisoformat(_text(raw.get("retrieved_at"), 40)),
        source_note=_text(raw.get("source_note"), 400),
        equipment=tuple(
            EquipmentEntry(
                id=_text(item.get("id"), 60),
                side=Side(_text(item.get("side"), 2)),
                group=_text(item.get("group"), 40),
                subgroup=_text(item.get("subgroup"), 40),
                name=_text(item.get("name")),
                origin=_text(item.get("origin"), 80),
                role=_text(item.get("role"), 160),
                description=_text(item.get("description"), MAX_TEXT),
                numbers=_optional(item.get("numbers"), 400),
                wikidata_id=_qid(item.get("wikidata_id")),
                image_id=_image_id(item.get("image_id")),
                as_of=_date(item.get("as_of")),
                links=_links(item.get("links") or []),
            )
            for item in raw.get("equipment") or []
        ),
        forces=tuple(
            ForceNode(
                id=_text(item.get("id"), 60),
                side=Side(_text(item.get("side"), 2)),
                parent_id=_optional(item.get("parent_id"), 60),
                name=_text(item.get("name")),
                role=_text(item.get("role"), MAX_TEXT),
                commander=_optional(item.get("commander"), 120),
                figure_id=_optional(item.get("figure_id"), 60),
                strength=_optional(item.get("strength"), 400),
                wikidata_id=_qid(item.get("wikidata_id")),
                as_of=_date(item.get("as_of")),
                links=_links(item.get("links") or []),
            )
            for item in raw.get("forces") or []
        ),
        phases=tuple(
            TimelinePhase(
                id=_text(item.get("id"), 60),
                label=_text(item.get("label")),
                start=_date(item.get("start")),
                end=_date(item["end"]) if item.get("end") else None,
                summary=_text(item.get("summary"), MAX_TEXT),
            )
            for item in raw.get("phases") or []
        ),
        events=tuple(
            TimelineEvent(
                id=_text(item.get("id"), 60),
                phase_id=_text(item.get("phase_id"), 60),
                on=_date(item.get("on")),
                title=_text(item.get("title")),
                text=_text(item.get("text"), MAX_TEXT),
                theme=_text(item.get("theme"), 40),
                wikidata_id=_qid(item.get("wikidata_id")),
                image_id=_image_id(item.get("image_id")),
                links=_links(item.get("links") or []),
            )
            for item in raw.get("events") or []
        ),
        images=images,
    )


@lru_cache(maxsize=1)
def load_reference_catalogue() -> ReferenceCatalogue | None:
    resource = files("ase.resources").joinpath(RESOURCE)
    if not resource.is_file():
        return None
    return parse_catalogue(json.loads(resource.read_text(encoding="utf-8")))


@lru_cache(maxsize=256)
def load_reference_image(image_id: str) -> bytes | None:
    """One cached JPEG by id; ids are validated before touching the package tree."""
    if not IMAGE_ID.fullmatch(image_id):
        return None
    resource = files("ase.resources").joinpath(IMAGE_FOLDER).joinpath(f"{image_id}.jpg")
    if not resource.is_file():
        return None
    data = resource.read_bytes()
    return data if len(data) <= MAX_IMAGE_BYTES else None

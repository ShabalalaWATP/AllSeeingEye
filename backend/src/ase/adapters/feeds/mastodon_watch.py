"""The reviewed Mastodon instances and hashtags this deployment polls.

Rows, not code. Each instance was checked by hand before it was added: its `robots.txt`
allows `/api/v1/timelines/tag/`, its public tag timeline answers without a key or an
account, and the tags carried there returned recent posts. The bounds below exist for
two reasons the reader cannot see from the data: requests per hour to a volunteer-run
instance, and `ase.domain.social.MAX_TERMS`, which the packaged tags share with each
operator's own collection vocabulary. Widening the tag list therefore costs an operator
their own search terms, so the distinct set is kept to half the cap.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

# Requires Python >=3.12; this standard-library API is supported.
# nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
from importlib import resources
from typing import Any

MAX_INSTANCES = 8
MAX_TAGS_PER_INSTANCE = 12
MAX_DISTINCT_TAGS = 16
MIN_POLL_MINUTES = 5
MAX_POLL_MINUTES = 120
DEFAULT_POLL_MINUTES = 15
# One request start per second per instance, so a restart cannot burst a volunteer host.
HOST_REQUEST_SPACING_SECONDS = 1.0
_HOST = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
_TAG = re.compile(r"^[a-z0-9_]{2,40}$")


@dataclass(frozen=True, slots=True)
class InstanceWatch:
    """One public instance, the hashtags read there, and how often they are read."""

    instance: str
    tags: tuple[str, ...]
    minutes: int


def _tags(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise ValueError("Mastodon watch tags must be a list")
    seen: list[str] = []
    for value in raw:
        tag = str(value).strip().lstrip("#").lower()
        if not _TAG.match(tag):
            raise ValueError(f"Unsupported Mastodon hashtag: {value!r}")
        if tag not in seen:
            seen.append(tag)
    if not seen or len(seen) > MAX_TAGS_PER_INSTANCE:
        raise ValueError(f"An instance carries 1 to {MAX_TAGS_PER_INSTANCE} hashtags")
    return tuple(seen)


def _minutes(raw: Any) -> int:
    minutes = int(raw) if isinstance(raw, int) else DEFAULT_POLL_MINUTES
    if not MIN_POLL_MINUTES <= minutes <= MAX_POLL_MINUTES:
        raise ValueError(f"Poll interval must be {MIN_POLL_MINUTES} to {MAX_POLL_MINUTES} minutes")
    return minutes


def _entry(raw: object) -> InstanceWatch:
    if not isinstance(raw, dict):
        raise ValueError("Each Mastodon watch entry must be an object")
    instance = str(raw.get("instance") or "").strip().lower()
    if not _HOST.match(instance) or len(instance) > 100:
        raise ValueError(f"Unsupported Mastodon instance: {instance!r}")
    return InstanceWatch(instance, _tags(raw.get("tags")), _minutes(raw.get("minutes")))


def parse_watch(data: object) -> tuple[InstanceWatch, ...]:
    """Validate a watch document; a malformed row is a packaging fault, not user input."""
    rows = data.get("mastodon", []) if isinstance(data, dict) else []
    if not isinstance(rows, list) or not rows or len(rows) > MAX_INSTANCES:
        raise ValueError(f"The Mastodon watch list carries 1 to {MAX_INSTANCES} instances")
    watches = tuple(_entry(row) for row in rows)
    if len({watch.instance for watch in watches}) != len(watches):
        raise ValueError("Mastodon instances must be listed once")
    if len(watch_terms(watches)) > MAX_DISTINCT_TAGS:
        raise ValueError(f"At most {MAX_DISTINCT_TAGS} distinct hashtags may be watched")
    return watches


def load_watch() -> tuple[InstanceWatch, ...]:
    """The packaged, reviewed watch list."""
    raw = resources.files("ase.resources").joinpath("social_watch.json").read_text("utf-8")
    return parse_watch(json.loads(raw))


def watch_terms(watches: tuple[InstanceWatch, ...] | None = None) -> tuple[str, ...]:
    """The distinct hashtags, for the social board's packaged vocabulary."""
    rows = load_watch() if watches is None else watches
    return tuple(sorted({tag for watch in rows for tag in watch.tags}))


def watch_host_intervals(
    watches: tuple[InstanceWatch, ...] | None = None,
) -> dict[str, float]:
    """Per-instance request spacing for the shared host pacer."""
    rows = load_watch() if watches is None else watches
    return {watch.instance: HOST_REQUEST_SPACING_SECONDS for watch in rows}

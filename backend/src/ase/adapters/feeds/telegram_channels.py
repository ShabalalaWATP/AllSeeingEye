"""The curated Telegram channel set, loaded from packaged JSON and checked once at import.

Read ``telegram_channel_registry`` for what an entry means and why none of these channels
is treated as an observer. The rows live in ``ase/resources/feeds/telegram_<area>.json``,
split by area, each file with its own provenance note. Every field is validated here and
by ``TelegramChannel`` itself; a malformed row fails import.
"""

from __future__ import annotations

from typing import Final, cast, get_args

from ase.adapters.feeds.telegram_channel_registry import (
    TelegramChannel,
    Viewpoint,
    channel,
    channel_url,
    preview_url,
    validate,
)
from ase.adapters.packaged_json import (
    choice,
    fields,
    integer,
    language,
    lines,
    load_resource,
    name,
    records,
    text,
    unique,
)

__all__ = [
    "TELEGRAM_CHANNELS",
    "TelegramChannel",
    "Viewpoint",
    "channel_url",
    "preview_url",
    "telegram_channels",
]

AREAS: Final = ("ukraine", "russia", "correspondents", "world")
_CHANNEL_KEYS: Final = (
    "username",
    "name",
    "operator",
    "topic",
    "reason",
    "viewpoint",
    "alignment",
    "language",
    "poll_minutes",
)


def _channel(where: str, value: object) -> TelegramChannel:
    row = fields(where, value, _CHANNEL_KEYS)
    viewpoint = choice(f"{where}.viewpoint", row["viewpoint"], get_args(Viewpoint))
    return channel(
        text(f"{where}.username", row["username"], limit=32),
        text(f"{where}.name", row["name"], limit=120),
        text(f"{where}.operator", row["operator"], limit=160),
        name(f"{where}.topic", row["topic"]),
        text(f"{where}.reason", row["reason"], limit=400),
        cast(Viewpoint, viewpoint),
        alignment=text(f"{where}.alignment", row["alignment"], empty=True, limit=80),
        language=language(f"{where}.language", row["language"]),
        # TelegramChannel enforces the polite polling range itself.
        minutes=integer(f"{where}.poll_minutes", row["poll_minutes"], 1, 24 * 60),
    )


def _area(area: str) -> tuple[TelegramChannel, ...]:
    where = f"feeds/telegram_{area}.json"
    data = fields(where, load_resource("feeds", f"telegram_{area}.json"), ("about", "groups"))
    lines(f"{where}.about", data["about"])
    result: list[TelegramChannel] = []
    groups = records(f"{where}.groups", data["groups"], 16)
    for index, value in enumerate(groups):
        group = fields(f"{where}.groups[{index}]", value, ("group", "channels"))
        label = f"{where}.{name(f'{where}.groups[{index}].group', group['group'])}"
        rows = records(label, group["channels"], 100)
        result.extend(_channel(f"{label}[{row}]", item) for row, item in enumerate(rows))
    unique(f"{where} groups", [str(group["group"]) for group in groups])
    return tuple(result)


TELEGRAM_CHANNELS: tuple[TelegramChannel, ...] = validate(
    tuple(entry for area in AREAS for entry in _area(area))
)


def telegram_channels(disabled: frozenset[str] = frozenset()) -> tuple[TelegramChannel, ...]:
    """The curated set, less anything the operator has switched off by source id."""
    return tuple(entry for entry in TELEGRAM_CHANNELS if entry.source_id not in disabled)

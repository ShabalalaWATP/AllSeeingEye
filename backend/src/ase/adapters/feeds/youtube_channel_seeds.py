"""Load the reviewed YouTube channels this deployment polls through the Data API v3.

Rows, not code: they are packaged in ``ase/resources/feeds/youtube_channels.json``, grouped
by what the operator asked to watch, with the provenance note for the whole list. Every
field is validated here and by ``YouTubeChannel`` itself, so a malformed row fails import.
Grading rules live beside the row type in `youtube_channels.py`.
"""

from __future__ import annotations

from typing import Final, cast, get_args

from ase.adapters.feeds.youtube_channels import MAX_CHANNELS, ChannelKind, YouTubeChannel
from ase.adapters.packaged_json import (
    choice,
    fields,
    flag,
    integer,
    language,
    lines,
    load_resource,
    name,
    names,
    records,
    text,
    unique,
)
from ase.domain.events import Reliability

RESOURCE: Final = "youtube_channels.json"
_CHANNEL_KEYS: Final = (
    "source_id",
    "name",
    "organisation",
    "handle",
    "topics",
    "reliability",
    "kind",
    "state_aligned",
    "language",
    "poll_minutes",
)


def _channel(where: str, value: object) -> YouTubeChannel:
    row = fields(where, value, _CHANNEL_KEYS, ("channel_id", "note"))
    if "note" in row:
        text(f"{where}.note", row["note"])
    kind = choice(f"{where}.kind", row["kind"], get_args(ChannelKind))
    grades = {grade.value for grade in Reliability}
    return YouTubeChannel(
        source_id=name(f"{where}.source_id", row["source_id"]),
        name=text(f"{where}.name", row["name"], limit=120),
        organisation=text(f"{where}.organisation", row["organisation"], limit=160),
        handle=text(f"{where}.handle", row["handle"], limit=40),
        topics=names(f"{where}.topics", row["topics"]),
        reliability=Reliability(choice(f"{where}.reliability", row["reliability"], grades)),
        kind=cast(ChannelKind, kind),
        channel_id=text(f"{where}.channel_id", row["channel_id"]) if "channel_id" in row else "",
        state_aligned=flag(f"{where}.state_aligned", row["state_aligned"]),
        language=language(f"{where}.language", row["language"]),
        # YouTubeChannel enforces the reviewed polling range itself.
        minutes=integer(f"{where}.poll_minutes", row["poll_minutes"], 1, 24 * 60),
    )


def _read() -> tuple[YouTubeChannel, ...]:
    where = f"feeds/{RESOURCE}"
    data = fields(where, load_resource("feeds", RESOURCE), ("about", "groups"))
    lines(f"{where}.about", data["about"])
    result: list[YouTubeChannel] = []
    groups = records(f"{where}.groups", data["groups"], 32)
    for index, value in enumerate(groups):
        group = fields(f"{where}.groups[{index}]", value, ("group", "about", "channels"))
        label = f"{where}.{name(f'{where}.groups[{index}].group', group['group'])}"
        text(f"{label}.about", group["about"])
        rows = records(label, group["channels"], MAX_CHANNELS)
        result.extend(_channel(f"{label}[{row}]", item) for row, item in enumerate(rows))
    unique(f"{where} groups", [str(group["group"]) for group in groups])
    return tuple(result)


CHANNELS: tuple[YouTubeChannel, ...] = _read()


def load_channels() -> tuple[YouTubeChannel, ...]:
    """The packaged, reviewed channel list. A malformed row is a packaging fault."""
    if not CHANNELS or len(CHANNELS) > MAX_CHANNELS:
        raise ValueError(f"The YouTube channel list carries 1 to {MAX_CHANNELS} channels")
    for field in (
        [row.source_id for row in CHANNELS],
        [row.handle.lower() for row in CHANNELS],
        [row.channel_id for row in CHANNELS if row.channel_id],
    ):
        if len(set(field)) != len(field):
            raise ValueError("Each YouTube channel is listed once")
    return CHANNELS

"""The curated Telegram channel set, assembled and checked once at import.

Read ``telegram_channel_registry`` for what an entry means and why none of these channels
is treated as an observer. The groups themselves live beside this module, split by area so
no single file grows past the repository's length limit.
"""

from __future__ import annotations

from ase.adapters.feeds.telegram_channel_registry import (
    TelegramChannel,
    Viewpoint,
    channel_url,
    preview_url,
    validate,
)
from ase.adapters.feeds.telegram_channels_correspondents import CORRESPONDENT_CHANNELS
from ase.adapters.feeds.telegram_channels_russia import RUSSIA_CHANNELS
from ase.adapters.feeds.telegram_channels_ukraine import UKRAINE_CHANNELS
from ase.adapters.feeds.telegram_channels_world import WORLD_CHANNELS

__all__ = [
    "TELEGRAM_CHANNELS",
    "TelegramChannel",
    "Viewpoint",
    "channel_url",
    "preview_url",
    "telegram_channels",
]

TELEGRAM_CHANNELS: tuple[TelegramChannel, ...] = validate(
    (*UKRAINE_CHANNELS, *RUSSIA_CHANNELS, *CORRESPONDENT_CHANNELS, *WORLD_CHANNELS)
)


def telegram_channels(disabled: frozenset[str] = frozenset()) -> tuple[TelegramChannel, ...]:
    """The curated set, less anything the operator has switched off by source id."""
    return tuple(entry for entry in TELEGRAM_CHANNELS if entry.source_id not in disabled)

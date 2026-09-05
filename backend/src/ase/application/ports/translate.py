"""Translation of short texts into English, in batches."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class Translator(Protocol):
    async def translate(self, items: Sequence[tuple[str, str]]) -> list[str | None]:
        """English for each (text, language) pair, in order; None where no translation came.

        Raises TranslatorUnavailable when nothing can translate right now (no profile with
        the translation role, no encryption key), so the caller can wait rather than retry.
        """
        ...


class TranslatorUnavailable(Exception):
    """No translator is configured or usable at the moment."""

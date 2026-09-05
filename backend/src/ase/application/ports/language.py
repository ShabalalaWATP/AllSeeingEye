"""Language detection for short texts (titles), used by the pipeline."""

from __future__ import annotations

from typing import Protocol


class LanguageDetector(Protocol):
    def detect(self, text: str) -> str | None:
        """ISO 639-1 code in lower case, or None when the text gives no confident answer."""
        ...

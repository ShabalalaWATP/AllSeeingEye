"""Language detection with py3langid, restricted to the languages the feeds carry.

The model loads on first use because it takes a moment and most tests never need it. A
guess below the confidence floor is reported as unknown rather than wrong; titles are
short and the stage only runs for events whose feed could not name a language.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from py3langid.langid import MODEL_DIR, MODEL_FILE, LanguageIdentifier

from ase.domain.languages import LANGUAGES

DEFAULT_LANGUAGES = tuple(
    dict.fromkeys(
        language.detector_code for language in LANGUAGES if language.detector_code is not None
    )
)
MIN_CHARS = 12
MIN_CONFIDENCE = 0.7


class LangidDetector:
    def __init__(
        self, languages: Sequence[str] = DEFAULT_LANGUAGES, *, floor: float = MIN_CONFIDENCE
    ) -> None:
        self._languages = list(languages)
        self._floor = floor
        self._identifier: LanguageIdentifier | None = None

    def _engine(self) -> LanguageIdentifier:
        if self._identifier is None:
            model = Path(MODEL_DIR) / MODEL_FILE
            identifier = LanguageIdentifier.from_modelpath(str(model), norm_probs=True)
            identifier.set_languages(self._languages)
            self._identifier = identifier
        return self._identifier

    def detect(self, text: str) -> str | None:
        sample = " ".join(text.split())
        if len(sample) < MIN_CHARS:
            return None
        code, probability = self._engine().classify(sample)
        return str(code) if float(probability) >= self._floor else None


class NullDetector:
    """Detection switched off: every unknown language stays unknown."""

    def detect(self, text: str) -> str | None:
        return None

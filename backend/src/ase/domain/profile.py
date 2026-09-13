"""Personal presentation and research defaults, never evidence or access policy."""

import re
from dataclasses import dataclass
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ase.domain.languages import ReportLanguage, language_capability, valid_language_code

DateFormat = Literal["day_first", "month_first", "iso"]
ReportStyle = Literal["briefing", "assessment"]
ExportFormat = Literal["pdf", "docx", "md"]
AppearanceTheme = Literal[
    "obsidian", "slate", "light", "midnight", "aurora", "phosphor", "crimson", "graphite"
]
APPEARANCE_THEMES: tuple[AppearanceTheme, ...] = (
    "obsidian",
    "slate",
    "light",
    "midnight",
    "aurora",
    "phosphor",
    "crimson",
    "graphite",
)


@dataclass(frozen=True, slots=True)
class PersonalProfile:
    display_name: str
    timezone: str = "UTC"
    date_format: DateFormat = "day_first"
    research_mode: Literal["quick", "detailed", "advanced"] = "quick"
    research_languages: tuple[str, ...] = ("en",)
    research_window_days: Literal[1, 3, 7, 14] = 3
    research_country: str | None = None
    report_language: ReportLanguage = "en"
    report_style: ReportStyle = "assessment"
    export_format: ExportFormat = "pdf"
    appearance_theme: AppearanceTheme = "obsidian"
    reduced_motion: bool = False

    def __post_init__(self) -> None:
        name = self.display_name.strip()
        if not 1 <= len(name) <= 120 or any(ord(char) < 32 for char in name):
            raise ValueError("Display name must contain 1 to 120 printable characters")
        object.__setattr__(self, "display_name", name)
        self._validate_preferences()

    def _validate_preferences(self) -> None:
        try:
            if len(self.timezone) > 100:
                raise ValueError("Invalid timezone")
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Choose a valid IANA timezone") from exc
        if self.date_format not in ("day_first", "month_first", "iso"):
            raise ValueError("Invalid date format")
        if self.research_mode not in ("quick", "detailed", "advanced"):
            raise ValueError("Invalid research mode")
        if self.research_window_days not in (1, 3, 7, 14):
            raise ValueError("Research window must be 1, 3, 7 or 14 days")
        if self.research_country is not None and not re.fullmatch(
            r"[A-Z]{2}", self.research_country
        ):
            raise ValueError("Country must use a two-letter uppercase code")
        if not 1 <= len(self.research_languages) <= 8:
            raise ValueError("Choose between one and eight source languages")
        for language in (*self.research_languages, self.report_language):
            if not valid_language_code(language):
                raise ValueError("Invalid language code")
        capability = language_capability(self.report_language)
        if capability is None or not capability.report_supported:
            raise ValueError("Unsupported report language")
        object.__setattr__(
            self, "research_languages", tuple(dict.fromkeys(self.research_languages))
        )
        self._validate_presentation()

    def _validate_presentation(self) -> None:
        if self.report_style not in ("briefing", "assessment"):
            raise ValueError("Invalid report style")
        if self.export_format not in ("pdf", "docx", "md"):
            raise ValueError("Invalid export format")
        if self.appearance_theme not in APPEARANCE_THEMES:
            raise ValueError("Invalid appearance theme")
        if not isinstance(self.reduced_motion, bool):
            raise ValueError("Reduced motion must be a boolean")

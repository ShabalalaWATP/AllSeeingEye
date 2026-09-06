"""Strict public profile contract with no identity or policy mutation fields."""

from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ase.domain.languages import LANGUAGE_CODE_PATTERN, ReportLanguage
from ase.domain.profile import DateFormat, ExportFormat, ReportStyle

LanguageCode = Annotated[str, Field(pattern=LANGUAGE_CODE_PATTERN)]


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    display_name: str
    timezone: str
    date_format: DateFormat
    research_mode: Literal["quick", "detailed"]
    research_languages: list[str]
    research_window_days: Literal[1, 3, 7, 14]
    research_country: str | None
    report_language: ReportLanguage
    report_style: ReportStyle
    export_format: ExportFormat


class ProfileUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    timezone: str | None = Field(default=None, min_length=1, max_length=100)
    date_format: DateFormat | None = None
    research_mode: Literal["quick", "detailed"] | None = None
    research_languages: list[LanguageCode] | None = Field(default=None, min_length=1, max_length=8)
    research_window_days: Literal[1, 3, 7, 14] | None = None
    research_country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    report_language: ReportLanguage | None = None
    report_style: ReportStyle | None = None
    export_format: ExportFormat | None = None

    @field_validator("research_window_days", mode="before")
    @classmethod
    def integer_window(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("Research window must be a number of days")
        return value

    @field_validator("display_name")
    @classmethod
    def valid_name(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value or any(ord(char) < 32 for char in value):
                raise ValueError("Provide a printable display name")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ValueError, ZoneInfoNotFoundError) as exc:
                raise ValueError("Choose a valid IANA timezone") from exc
        return value

    @model_validator(mode="after")
    def reject_null_preferences(self) -> Self:
        if any(
            getattr(self, name) is None for name in self.model_fields_set - {"research_country"}
        ):
            raise ValueError("Only the country preference may be null")
        return self

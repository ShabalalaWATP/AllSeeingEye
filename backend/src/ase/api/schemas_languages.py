"""Shared language choices with explicit detection, edition and PDF limitations."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class SearchEditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hl: str
    gl: str
    ceid: str


class LanguageCapabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    native_label: str
    direction: Literal["ltr", "rtl"]
    report_supported: bool
    pdf_supported: bool
    detector_code: str | None
    google_news_edition: SearchEditionOut | None


class LanguageCatalogueOut(BaseModel):
    version: Literal["1"] = "1"
    languages: list[LanguageCapabilityOut]

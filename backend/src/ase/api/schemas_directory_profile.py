"""Strict schemas for owner-controlled directory profiles and safe discovery."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ase.domain.directory_profile import (
    MAX_BIOGRAPHY,
    MAX_EXPERTISE,
    MAX_EXPERTISE_LABEL,
    MAX_JOB_TITLE,
    MAX_LANGUAGES,
    MAX_ORGANISATION,
    USERNAME_PATTERN,
    DirectoryEntry,
    DirectoryPage,
    DirectoryProfile,
)
from ase.domain.languages import LANGUAGE_CODE_PATTERN

LanguageCode = Annotated[str, Field(pattern=LANGUAGE_CODE_PATTERN)]
ExpertiseLabel = Annotated[str, Field(min_length=1, max_length=MAX_EXPERTISE_LABEL)]


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError("Text must contain printable characters")
    return value


class DirectoryProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str | None
    job_title: str | None
    organisation: str | None
    biography: str | None
    country: str | None
    languages: list[str]
    expertise: list[str]
    timezone: str | None
    is_discoverable: bool
    show_timezone: bool
    revision: int
    updated_at: datetime | None

    @classmethod
    def from_entity(cls, profile: DirectoryProfile) -> Self:
        return cls(
            user_id=profile.user_id,
            username=profile.username,
            job_title=profile.job_title,
            organisation=profile.organisation,
            biography=profile.biography,
            country=profile.country,
            languages=list(profile.languages),
            expertise=list(profile.expertise),
            timezone=profile.timezone if profile.show_timezone else None,
            is_discoverable=profile.is_discoverable,
            show_timezone=profile.show_timezone,
            revision=profile.revision,
            updated_at=profile.updated_at,
        )


class DirectoryProfileUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    username: str | None = Field(default=None, min_length=3, max_length=32)
    job_title: str | None = Field(default=None, max_length=MAX_JOB_TITLE)
    organisation: str | None = Field(default=None, max_length=MAX_ORGANISATION)
    biography: str | None = Field(default=None, max_length=MAX_BIOGRAPHY)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    languages: list[LanguageCode] | None = Field(default=None, max_length=MAX_LANGUAGES)
    expertise: list[ExpertiseLabel] | None = Field(default=None, max_length=MAX_EXPERTISE)
    timezone: str | None = Field(default=None, max_length=100)
    is_discoverable: bool | None = None
    show_timezone: bool | None = None
    expected_revision: int | None = Field(default=None, ge=1)

    @field_validator("username")
    @classmethod
    def valid_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("Username must be 3 to 32 lowercase letters, numbers or underscores")
        return value

    @field_validator("job_title", "organisation", "biography")
    @classmethod
    def valid_text(cls, value: str | None) -> str | None:
        return _clean_text(value)

    @field_validator("country")
    @classmethod
    def valid_country(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if len(value) != 2 or not value.isascii() or not value.isalpha():
            raise ValueError("Country must use a two-letter code")
        return value

    @field_validator("languages")
    @classmethod
    def valid_languages(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return list(dict.fromkeys(item.strip() for item in value))

    @field_validator("expertise")
    @classmethod
    def valid_expertise(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [_clean_text(item) for item in value]
        result: list[str] = []
        for item in cleaned:
            assert item is not None  # noqa: S101
            if item.casefold() not in {existing.casefold() for existing in result}:
                result.append(item)
        return result

    @model_validator(mode="after")
    def has_update(self) -> Self:
        if not self.model_fields_set - {"expected_revision"}:
            raise ValueError("Provide at least one directory profile field")
        return self

    def to_changes(self) -> dict[str, object]:
        changes = self.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if "languages" in changes:
            changes["languages"] = tuple(changes["languages"] or ())
        if "expertise" in changes:
            changes["expertise"] = tuple(changes["expertise"] or ())
        return changes


class DirectoryUserOut(BaseModel):
    user_id: UUID
    username: str
    display_name: str
    job_title: str | None
    organisation: str | None
    biography: str | None
    country: str | None
    languages: list[str]
    expertise: list[str]
    timezone: str | None

    @classmethod
    def from_entry(cls, entry: DirectoryEntry) -> Self:
        profile = entry.profile
        assert profile.username is not None  # noqa: S101
        return cls(
            user_id=profile.user_id,
            username=profile.username,
            display_name=entry.display_name,
            job_title=profile.job_title,
            organisation=profile.organisation,
            biography=profile.biography,
            country=profile.country,
            languages=list(profile.languages),
            expertise=list(profile.expertise),
            timezone=profile.timezone if profile.show_timezone else None,
        )


class DirectoryPageOut(BaseModel):
    items: list[DirectoryUserOut]
    total: int
    offset: int
    limit: int
    next_offset: int | None

    @classmethod
    def from_page(cls, page: DirectoryPage) -> Self:
        return cls(
            items=[DirectoryUserOut.from_entry(item) for item in page.items],
            total=page.total,
            offset=page.offset,
            limit=page.limit,
            next_offset=page.next_offset,
        )

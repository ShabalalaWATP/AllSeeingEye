"""Public, opt-in operator directory profiles.

Directory fields are deliberately separate from :mod:`ase.domain.profile`, which
contains private preferences.  A directory profile is safe to return to another
authenticated operator only when the owner has explicitly enabled discovery.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ase.domain.languages import valid_language_code

USERNAME_PATTERN: Final = re.compile(r"^[a-z0-9_]{3,32}$")
COUNTRY_PATTERN: Final = re.compile(r"^[A-Z]{2}$")
RESERVED_USERNAMES: Final = frozenset(
    {
        "admin",
        "administrator",
        "all",
        "everyone",
        "me",
        "root",
        "support",
        "system",
        "team",
        "teams",
        "user",
    }
)
MAX_JOB_TITLE = 120
MAX_ORGANISATION = 120
MAX_BIOGRAPHY = 500
MAX_EXPERTISE_LABEL = 40
MAX_EXPERTISE = 10
MAX_LANGUAGES = 8
AVATAR_DIGEST_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")


class DirectoryField(StrEnum):
    """Optional profile fields whose directory visibility the owner controls."""

    JOB_TITLE = "job_title"
    ORGANISATION = "organisation"
    BIOGRAPHY = "biography"
    COUNTRY = "country"
    LANGUAGES = "languages"
    EXPERTISE = "expertise"
    TIMEZONE = "timezone"


# Timezone is private by default; the other self-described fields are shown once filled in.
DEFAULT_VISIBLE_FIELDS: Final = frozenset(DirectoryField) - {DirectoryField.TIMEZONE}


def normalise_username(value: str | None) -> str | None:
    """Return the canonical handle or raise a domain validation error."""

    if value is None:
        return None
    username = value.strip().lower()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Username must be 3 to 32 lowercase letters, numbers or underscores")
    if username in RESERVED_USERNAMES:
        raise ValueError("That username is reserved")
    return username


def _text(value: str | None, maximum: int, label: str) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or len(value) > maximum:
        raise ValueError(f"{label} must contain 1 to {maximum} characters")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError(f"{label} contains an unsupported control character")
    return value


def _country(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    if not COUNTRY_PATTERN.fullmatch(value):
        raise ValueError("Country must use a two-letter uppercase code")
    return value


def _timezone(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    try:
        if len(value) > 100:
            raise ValueError
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("Choose a valid IANA timezone") from exc
    return value


def _languages(values: tuple[str, ...]) -> tuple[str, ...]:
    if len(values) > MAX_LANGUAGES:
        raise ValueError(f"Choose at most {MAX_LANGUAGES} languages")
    normalised = tuple(dict.fromkeys(value.strip() for value in values))
    if any(not valid_language_code(value) for value in normalised):
        raise ValueError("Choose valid language codes")
    return normalised


def _expertise(values: tuple[str, ...]) -> tuple[str, ...]:
    if len(values) > MAX_EXPERTISE:
        raise ValueError(f"Choose at most {MAX_EXPERTISE} expertise labels")
    result: list[str] = []
    for value in values:
        cleaned = _text(value, MAX_EXPERTISE_LABEL, "Expertise label")
        assert cleaned is not None  # noqa: S101
        if cleaned.casefold() not in {item.casefold() for item in result}:
            result.append(cleaned)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class DirectoryProfile:
    """The owner-controlled public directory projection for one account."""

    user_id: UUID
    username: str | None = None
    job_title: str | None = None
    organisation: str | None = None
    biography: str | None = None
    country: str | None = None
    languages: tuple[str, ...] = ()
    expertise: tuple[str, ...] = ()
    timezone: str | None = None
    is_discoverable: bool = False
    visible_fields: frozenset[DirectoryField] = field(default=DEFAULT_VISIBLE_FIELDS)
    avatar_sha256: str | None = None
    revision: int = 1
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "username", normalise_username(self.username))
        object.__setattr__(self, "job_title", _text(self.job_title, MAX_JOB_TITLE, "Job title"))
        object.__setattr__(
            self, "organisation", _text(self.organisation, MAX_ORGANISATION, "Organisation")
        )
        object.__setattr__(self, "biography", _text(self.biography, MAX_BIOGRAPHY, "Biography"))
        object.__setattr__(self, "country", _country(self.country))
        object.__setattr__(self, "languages", _languages(tuple(self.languages)))
        object.__setattr__(self, "expertise", _expertise(tuple(self.expertise)))
        object.__setattr__(self, "timezone", _timezone(self.timezone))
        if not isinstance(self.is_discoverable, bool):
            raise ValueError("Directory visibility must be a boolean")
        try:
            visible = frozenset(DirectoryField(item) for item in self.visible_fields)
        except (TypeError, ValueError) as exc:
            raise ValueError("Choose supported directory fields") from exc
        object.__setattr__(self, "visible_fields", visible)
        if self.avatar_sha256 is not None and not AVATAR_DIGEST_PATTERN.fullmatch(
            self.avatar_sha256
        ):
            raise ValueError("Avatar digest is invalid")
        if self.is_discoverable and self.username is None:
            raise ValueError("Choose a username before enabling directory visibility")
        if self.revision < 1:
            raise ValueError("Directory profile revision must be positive")

    def shows(self, name: DirectoryField) -> bool:
        """Whether an optional field may appear in results seen by other accounts."""

        return name in self.visible_fields


@dataclass(frozen=True, slots=True)
class DirectoryEntry:
    """A discoverable profile joined to the account's non-sensitive display name."""

    profile: DirectoryProfile
    display_name: str


@dataclass(frozen=True, slots=True)
class DirectoryPage:
    items: tuple[DirectoryEntry, ...]
    total: int
    offset: int
    limit: int

    @property
    def next_offset(self) -> int | None:
        next_value = self.offset + len(self.items)
        return next_value if next_value < self.total else None

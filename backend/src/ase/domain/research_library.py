"""Private annotations about reports, independent of frozen content and sharing scope."""

from dataclasses import dataclass
from datetime import datetime

from ase.domain.report_records import ReportRecord


def normalise_tag(value: str) -> str:
    tag = value.strip().casefold()
    if not tag or len(tag) > 40 or any(ord(char) < 32 for char in tag):
        raise ValueError("Tags require 1 to 40 printable characters")
    return tag


@dataclass(frozen=True, slots=True)
class LibraryPreference:
    favourite: bool = False
    tags: tuple[str, ...] = ()
    note: str | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if type(self.favourite) is not bool or len(self.tags) > 12:
            raise ValueError("Choose a favourite flag and at most 12 tags")
        normalised = tuple(normalise_tag(tag) for tag in self.tags)
        if len(set(normalised)) != len(normalised):
            raise ValueError("Tags must be unique")
        object.__setattr__(self, "tags", normalised)
        if self.note is not None:
            if len(self.note) > 1000 or "\0" in self.note:
                raise ValueError("Notes must contain at most 1000 characters without null bytes")
            object.__setattr__(self, "note", self.note.strip() or None)


@dataclass(frozen=True, slots=True)
class LibraryItem:
    report: ReportRecord
    preference: LibraryPreference


@dataclass(frozen=True, slots=True)
class LibraryPage:
    items: tuple[LibraryItem, ...]
    total: int
    offset: int
    limit: int

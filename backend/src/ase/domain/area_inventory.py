"""Bounded packaged-register findings for one scope: counts, a short named list, provenance.

Nothing here is an observation. A register entry says that a public dataset recorded a
site, with the date that dataset was captured. It does not establish that the site
exists today, that it is operating, or that it is in the state recorded.
"""

from __future__ import annotations

from dataclasses import dataclass

INVENTORY_POLICY_VERSION = "ase-area-inventory-v1"
MAX_LISTED_ITEMS = 6
MAX_REGISTER_ENTRIES = 8
MAX_RECORDS_SCANNED = 20_000

RECORD_CAVEAT = (
    "A register record is not evidence of a site's current state: it records that a public "
    "dataset held this site at the snapshot date, not that the site exists today, is "
    "operating, or is what the record says. Coverage is uneven between countries and no "
    "register here is complete, so an absence is not clearance."
)


@dataclass(frozen=True, slots=True)
class RegisterItem:
    """One named record, without coordinates: a register entry is not a located event."""

    name: str
    country: str | None
    precision: str
    url: str | None

    def __post_init__(self) -> None:
        if not self.name or len(self.name) > 200 or len(self.precision) > 60:
            raise ValueError("Register items need a bounded name and precision note")
        if self.country is not None and len(self.country) > 60:
            raise ValueError("Register item country labels are bounded")
        if self.url is not None and (len(self.url) > 500 or not self.url.startswith("https://")):
            raise ValueError("Register item links must be bounded HTTPS URLs")

    def describe(self) -> str:
        where = f", {self.country}" if self.country else ""
        return f"{self.name}{where} (position precision: {self.precision})"


@dataclass(frozen=True, slots=True)
class RegisterEntry:
    """One asset class inside one scope: how many records, and up to six of them named."""

    asset_class: str
    dataset_id: str
    dataset_name: str
    count: int
    listed: tuple[RegisterItem, ...]
    as_of: str
    attribution: str
    matched_by: str
    licence_url: str | None = None
    scanned_truncated: bool = False

    def __post_init__(self) -> None:
        if not self.asset_class or not self.dataset_id or not self.dataset_name:
            raise ValueError("Register entries need an asset class and a named dataset")
        if self.count < 0 or len(self.listed) > MAX_LISTED_ITEMS or len(self.listed) > self.count:
            raise ValueError("Register entries list at most six of their counted records")
        if not self.as_of or len(self.as_of) > 40 or len(self.attribution) > 500:
            raise ValueError("Register entries need a bounded snapshot date and attribution")
        if not self.matched_by or len(self.matched_by) > 200:
            raise ValueError("Register entries record how each record was matched to the scope")

    @property
    def unlisted(self) -> int:
        return max(0, self.count - len(self.listed))

    def title(self) -> str:
        return f"{self.dataset_name}: {self.count} record(s) in the requested scope"

    def describe(self) -> str:
        """Compact enough to survive the prompt's evidence summary bound."""
        named = "; ".join(item.describe() for item in self.listed) or "none listed"
        more = (
            f" {self.unlisted} further record(s) counted but not listed." if self.unlisted else ""
        )
        truncated = (
            " The scan reached its record bound, so the count is a floor."
            if self.scanned_truncated
            else ""
        )
        return (
            f"{self.count} record(s) matched by {self.matched_by}. "
            f"Named (up to {MAX_LISTED_ITEMS}): {named}.{more}{truncated} "
            f"Snapshot {self.as_of}. Register record, not evidence of current state."
        )

    def provenance(self) -> str:
        """The full dataset attribution and the caveat, for the collection receipt."""
        licence = f" Licence: {self.licence_url}." if self.licence_url else ""
        return (
            f"{self.dataset_name} ({self.dataset_id}), snapshot {self.as_of}: "
            f"{self.count} record(s) matched by {self.matched_by}. "
            f"{self.attribution}{licence}"
        )


def bound_entries(entries: tuple[RegisterEntry, ...]) -> tuple[RegisterEntry, ...]:
    """Register order is stable; only entries with records are carried forward."""
    kept = tuple(entry for entry in entries if entry.count > 0)
    if len(kept) > MAX_REGISTER_ENTRIES:
        raise ValueError("More register entries than the reviewed bound allows")
    return kept

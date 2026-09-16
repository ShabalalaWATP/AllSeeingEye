"""The curated Bluesky account registry: who is read, on what topic and why.

The packaged resource is the reviewed list. Every handle was resolved and read through
the application's own feed client before it was added; nothing here is discovered at
runtime, and no account is followed, authenticated or expanded from a post's links.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

# Requires Python >=3.12; this standard-library API is supported.
# nosemgrep: python.lang.compatibility.python37.python37-compatibility-importlib2
from importlib import resources
from typing import Any, Final

RESOURCE: Final = "bluesky_accounts.json"
VIEWPOINTS: Final = frozenset({"publisher", "researcher", "official_issuer", "state_aligned"})
# A viewpoint the UI must mark; "publisher" and "researcher" carry no extra tag.
MARKED_VIEWPOINTS: Final = frozenset({"official_issuer", "state_aligned"})
MAX_HANDLE = 64
MAX_REASON = 200
HANDLE_EXTRA: Final = frozenset({".", "-"})


@dataclass(frozen=True, slots=True)
class BlueskyAccount:
    """One reviewed public account: identity, subject and the reason it is carried."""

    handle: str
    operator: str
    topic: str
    viewpoint: str
    reason: str

    def __post_init__(self) -> None:
        if not valid_handle(self.handle):
            raise ValueError(f"Invalid Bluesky handle: {self.handle[:MAX_HANDLE]}")
        if not self.operator or not self.topic or not self.reason:
            raise ValueError(f"{self.handle}: operator, topic and reason are required")
        if self.viewpoint not in VIEWPOINTS:
            raise ValueError(f"{self.handle}: unknown viewpoint {self.viewpoint}")
        if len(self.reason) > MAX_REASON or len(self.operator) > MAX_REASON:
            raise ValueError(f"{self.handle}: registry text exceeds its bound")

    @property
    def tags(self) -> frozenset[str]:
        """Topic plus the viewpoint marks the UI shows, exactly as the news feeds do."""
        marks = {self.viewpoint} if self.viewpoint in MARKED_VIEWPOINTS else set()
        return frozenset({"bluesky", self.topic, *marks})

    @property
    def profile_url(self) -> str:
        return f"https://bsky.app/profile/{self.handle}"


def valid_handle(handle: str) -> bool:
    """An ASCII domain-style handle; nothing else may reach a request path."""
    return bool(
        handle
        and len(handle) <= MAX_HANDLE
        and "." in handle
        and not handle.startswith((".", "-"))
        and not handle.endswith((".", "-"))
        and ".." not in handle
        and all(char.isascii() and (char.isalnum() or char in HANDLE_EXTRA) for char in handle)
    )


def _account(entry: Any) -> BlueskyAccount:
    if not isinstance(entry, dict):
        raise ValueError("Each registry entry must be an object")
    return BlueskyAccount(
        handle=str(entry.get("handle", "")).strip().lower(),
        operator=str(entry.get("operator", "")).strip(),
        topic=str(entry.get("topic", "")).strip(),
        viewpoint=str(entry.get("viewpoint", "")).strip(),
        reason=str(entry.get("reason", "")).strip(),
    )


def load_accounts() -> tuple[BlueskyAccount, ...]:
    """Parse and validate the packaged registry; duplicates fail closed at import time."""
    raw = resources.files("ase.resources").joinpath(RESOURCE).read_text("utf-8")
    data = json.loads(raw)
    entries = data.get("accounts") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError("The Bluesky account registry is empty")
    accounts = tuple(_account(entry) for entry in entries)
    if len({account.handle for account in accounts}) != len(accounts):
        raise ValueError("Duplicate handle in the Bluesky account registry")
    return accounts


ACCOUNTS: Final[tuple[BlueskyAccount, ...]] = load_accounts()
TOPICS: Final[tuple[str, ...]] = tuple(sorted({account.topic for account in ACCOUNTS}))


def accounts_for(topics: frozenset[str]) -> tuple[BlueskyAccount, ...]:
    """The curated accounts on the requested topics, in registry order."""
    return tuple(account for account in ACCOUNTS if account.topic in topics)

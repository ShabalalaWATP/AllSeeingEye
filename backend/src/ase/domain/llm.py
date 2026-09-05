"""LLM profiles and the messages exchanged with a model, independent of any provider."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

MAX_OUTPUT_TOKENS = 32_000
MIN_OUTPUT_TOKENS = 64
KEY_HINT_CHARS = 4


class LlmRole(StrEnum):
    """What a profile is allowed to do in the generation pipeline."""

    DIRECTION = "direction"
    ASSESSMENT = "assessment"
    DEVIL = "devil"


def normalise_base_url(value: str) -> str:
    """An absolute http(s) URL without a trailing slash; local endpoints are allowed.

    Only administrators set these, and self-hosted models on localhost are the point of
    a self-hosted app, so private addresses are accepted here on purpose.
    """
    candidate = value.strip().rstrip("/")
    parts = urlsplit(candidate)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        msg = "The base URL must be an absolute http(s) address."
        raise ValueError(msg)
    if parts.username or parts.password:
        msg = "Credentials do not belong in the base URL."
        raise ValueError(msg)
    return candidate


def key_hint(api_key: str) -> str:
    """The last few characters, which is all the UI ever shows of a key."""
    return api_key[-KEY_HINT_CHARS:] if len(api_key) > KEY_HINT_CHARS else "…"


@dataclass(slots=True)
class LlmProfile:
    id: UUID
    name: str
    base_url: str
    model: str
    api_key_encrypted: str
    api_key_hint: str
    roles: frozenset[LlmRole]
    max_output_tokens: int
    temperature: float
    enabled: bool
    created_at: datetime
    updated_at: datetime

    def allows(self, role: LlmRole) -> bool:
        return self.enabled and role in self.roles


@dataclass(frozen=True, slots=True)
class LlmMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class LlmRequest:
    messages: tuple[LlmMessage, ...]
    max_output_tokens: int
    temperature: float
    json_schema: Mapping[str, Any] | None = None
    schema_name: str = "response"


@dataclass(frozen=True, slots=True)
class LlmResult:
    content: str
    model: str
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(slots=True)
class LlmUsage:
    """One call's cost, kept so the admin can see who used which profile for what."""

    at: datetime
    profile_id: UUID
    user_id: UUID | None
    purpose: str
    ok: bool
    latency_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    error: str | None = None
    id: int | None = None

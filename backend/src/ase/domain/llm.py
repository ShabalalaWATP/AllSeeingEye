"""LLM profiles and the messages exchanged with a model, independent of any provider."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from ipaddress import IPv4Address, ip_address, ip_network
from typing import Any, Literal
from urllib.parse import urlsplit
from uuid import UUID

MAX_OUTPUT_TOKENS = 32_000
MIN_OUTPUT_TOKENS = 64
MAX_API_KEY_LENGTH = 16_384
MAX_MODEL_ID_LENGTH = 2_048
KEY_HINT_CHARS = 4
LOCAL_MODEL_V4 = tuple(
    ip_network(cidr) for cidr in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
LOCAL_MODEL_V6 = ip_network("fc00::/7")


class LlmRole(StrEnum):
    """What a profile is allowed to do in the generation pipeline."""

    DIRECTION = "direction"
    ASSESSMENT = "assessment"
    DEVIL = "devil"
    TRANSLATION = "translation"
    EMBEDDINGS = "embeddings"


class ReasoningEffort(StrEnum):
    NONE = "none"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
    MAX = "max"


class LlmProvider(StrEnum):
    OPENAI_COMPATIBLE = "openai_compatible"
    BEDROCK = "bedrock"


TEXT_ROLES = frozenset({LlmRole.DIRECTION, LlmRole.ASSESSMENT, LlmRole.DEVIL, LlmRole.TRANSLATION})


def normalise_base_url(value: str) -> str:
    """An absolute http(s) URL without a trailing slash; local endpoints are allowed.

    Only administrators set these, and self-hosted models on localhost are the point of
    a self-hosted app, so private addresses are accepted here on purpose.
    """
    candidate = value.strip().rstrip("/")
    if any(ord(char) < 33 or ord(char) == 127 for char in candidate):
        raise ValueError("The base URL cannot contain whitespace or control characters.")
    parts = urlsplit(candidate)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        msg = "The base URL must be an absolute http(s) address."
        raise ValueError(msg)
    if parts.username or parts.password:
        msg = "Credentials do not belong in the base URL."
        raise ValueError(msg)
    if parts.query or parts.fragment:
        raise ValueError("The base URL cannot contain a query or fragment.")
    _ = parts.port  # Validate ports before any credential-bearing request.
    if parts.scheme == "http":
        host = parts.hostname or ""
        try:
            address = ip_address(host)
        except ValueError:
            local = host.lower() in {"localhost", "host.docker.internal"}
        else:
            local = address.is_loopback or (
                any(address in network for network in LOCAL_MODEL_V4)
                if isinstance(address, IPv4Address)
                else address in LOCAL_MODEL_V6
            )
        if not local:
            raise ValueError("Remote model endpoints must use HTTPS.")
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
    api_key_encrypted: str = field(repr=False)
    api_key_hint: str
    roles: frozenset[LlmRole]
    max_output_tokens: int
    temperature: float
    enabled: bool
    created_at: datetime
    updated_at: datetime
    reasoning_effort: ReasoningEffort | None = None
    revision: int = 1
    tested_at: datetime | None = None
    tested_revision: int | None = None
    tested_config_hash: str | None = None
    test_generation: int = 0
    provider: LlmProvider = LlmProvider.OPENAI_COMPATIBLE

    def allows(self, role: LlmRole) -> bool:
        return self.enabled and role in self.roles

    def token_budget(self, stage_limit: int) -> int:
        # Native reasoning defaults can consume completion tokens even without an
        # explicit effort setting. Let the tested administrator budget cover them.
        limit = (
            MAX_OUTPUT_TOKENS
            if self.provider is LlmProvider.BEDROCK
            or self.reasoning_effort is not None
            or self.model == "gpt-5.6-luna"
            else stage_limit
        )
        return min(self.max_output_tokens, limit)

    @property
    def config_hash(self) -> str:
        """Bind proof to saved request settings and the encrypted key revision.

        Operational enablement is excluded so explicit activation can enable a tested
        draft. Every ordinary edit still advances revision and invalidates its proof.
        """
        values: tuple[object, ...] = (
            str(self.id),
            self.revision,
            self.name,
            self.base_url,
            self.model,
            self.api_key_encrypted,
            sorted(self.roles),
            self.max_output_tokens,
            self.temperature,
            self.reasoning_effort,
        )
        if self.provider is not LlmProvider.OPENAI_COMPATIBLE:
            values += (f"provider:{self.provider.value}",)
        return hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).hexdigest()

    @property
    def is_tested(self) -> bool:
        return (
            self.tested_at is not None
            and self.tested_revision == self.revision
            and self.tested_config_hash == self.config_hash
        )


@dataclass(frozen=True, slots=True)
class LlmConnectionBinding:
    team_id: UUID | None
    profile_id: UUID
    profile_revision: int
    tested_config_hash: str
    activated_at: datetime
    activated_by: UUID
    revision: int = 1
    user_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.team_id is not None and self.user_id is not None:
            raise ValueError("An AI connection cannot target both a team and a person.")


@dataclass(frozen=True, slots=True)
class LlmImage:
    """One already sanitised PNG, never raw upload bytes or an external URL."""

    png: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.png, bytes) or not self.png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Model images must be sanitised PNG bytes.")
        if not 24 <= len(self.png) <= 1024 * 1024:
            raise ValueError("Model images must be at most 1 MiB.")


@dataclass(frozen=True, slots=True)
class LlmMessage:
    role: Literal["system", "user", "assistant"]
    content: str
    images: tuple[LlmImage, ...] = field(default=(), repr=False)

    def __post_init__(self) -> None:
        if len(self.images) > 1 or (self.images and self.role != "user"):
            raise ValueError("Only user messages may contain one sanitised image.")


@dataclass(frozen=True, slots=True)
class LlmRequest:
    messages: tuple[LlmMessage, ...]
    max_output_tokens: int
    temperature: float
    json_schema: Mapping[str, Any] | None = None
    schema_name: str = "response"
    reasoning_effort: ReasoningEffort | None = None
    provider: LlmProvider = LlmProvider.OPENAI_COMPATIBLE
    # Internal accounting identity only. Provider adapters never send this field.
    profile_id: UUID | None = None

    def __post_init__(self) -> None:
        if sum(len(message.images) for message in self.messages) > 6:
            raise ValueError("A model request may contain at most six sanitised images.")


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

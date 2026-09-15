"""Every source this deployment knows about, with a connection state any signed-in user may see.

The inventory never carries credential values, operator URLs or raw error text. It says
whether a source is collecting, waiting for a credential, disabled, or only used on demand,
and which documented setting unlocks it.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from ase.application.feeds.health import HealthRegistry, SourceHealth, SourceStatus
from ase.application.ports.feeds import FeedConnector
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.source_controls import source_control_keys
from ase.domain.sources import SourceSpec


class ConnectionState(StrEnum):
    CONNECTED = "connected"
    IDLE = "idle"
    DEGRADED = "degraded"
    FAILING = "failing"
    KEY_MISSING = "key_missing"
    KEY_UNVERIFIED = "key_unverified"
    ON_DEMAND = "on_demand"
    NOT_CONFIGURED = "not_configured"
    DISABLED_BY_ADMIN = "disabled_by_admin"
    DISABLED_BY_ENVIRONMENT = "disabled_by_environment"
    BLOCKED_UPSTREAM = "blocked_upstream"
    AVAILABLE = "available"


RequirementKind = Literal[
    "api_key",
    "credentials",
    "acknowledgement",
    "snapshot",
    "catalogue",
    "runtime",
    "model",
    "toggle",
    "endpoint",
]
RequirementOrigin = Literal["environment", "database", "none", "unknown"]


@dataclass(frozen=True, slots=True)
class SourceRequirement:
    """What a source needs beyond public access, and whether the server has it."""

    kind: RequirementKind
    satisfied: bool | None
    origin: RequirementOrigin
    setting: str | None
    note: str
    optional: bool = False


@dataclass(frozen=True, slots=True)
class SourceConnection:
    state: ConnectionState
    enabled: bool
    environment_disabled: bool
    active: bool
    requirement: SourceRequirement | None
    health: SourceHealth | None
    detail: str


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    spec: SourceSpec
    collection_mode: Literal["on_demand", "scheduled"]
    connection: SourceConnection


@dataclass(frozen=True, slots=True)
class PlatformConnection:
    """A keyed or optional service that is not a source, such as maps, mail or the model."""

    id: str
    name: str
    purpose: str
    state: ConnectionState
    requirement: SourceRequirement
    detail: str


_HEALTH_STATES = {
    SourceStatus.HEALTHY: ConnectionState.CONNECTED,
    SourceStatus.DEGRADED: ConnectionState.DEGRADED,
    SourceStatus.DISABLED: ConnectionState.FAILING,
    SourceStatus.IDLE: ConnectionState.IDLE,
}

RequirementResolver = Callable[[str], Awaitable[SourceRequirement | None]]


class SourceInventory:
    def __init__(
        self,
        connectors: Sequence[FeedConnector],
        research_specs: Sequence[SourceSpec],
        optional_specs: Sequence[SourceSpec],
        requirements: Mapping[str, SourceRequirement],
        health: HealthRegistry,
        admission: SourceAdmission,
        disabled: tuple[str, ...] = (),
        resolve_requirement: RequirementResolver | None = None,
        *,
        collecting: bool = True,
    ) -> None:
        self._connectors = {connector.spec.id: connector for connector in connectors}
        self._research = {spec.id: spec for spec in research_specs}
        # Live connectors win over static descriptions; optional connectors only fill gaps.
        self._specs: dict[str, SourceSpec] = {}
        self._specs.update(self._research)
        self._specs.update({spec.id: spec for spec in optional_specs})
        self._specs.update({key: connector.spec for key, connector in self._connectors.items()})
        self._requirements = dict(requirements)
        self._health, self._admission = health, admission
        self._disabled = frozenset(disabled)
        self._resolve = resolve_requirement
        self._collecting = collecting

    async def list(self) -> list[InventoryEntry]:
        enabled = await self._admission.enabled_many(tuple(self._specs))
        entries = []
        for key in sorted(self._specs, key=lambda key: (self._specs[key].name.casefold(), key)):
            spec = self._specs[key]
            requirement = self._requirements.get(key)
            if requirement is None and self._resolve is not None:
                requirement = await self._resolve(key)
            entries.append(self._entry(spec, enabled.get(key, False), requirement))
        return entries

    def _entry(
        self, spec: SourceSpec, enabled: bool, requirement: SourceRequirement | None
    ) -> InventoryEntry:
        scheduled = spec.id in self._connectors or spec.id not in self._research
        active = spec.id in self._connectors
        environment_disabled = any(key in self._disabled for key in source_control_keys(spec.id))
        health = self._health.get(spec.id) if active else None
        state, detail = _state(
            scheduled, active, enabled, environment_disabled, requirement, health
        )
        if state in _WAITING and not self._collecting:
            state, detail = ConnectionState.DISABLED_BY_ENVIRONMENT, FEEDS_OFF
        return InventoryEntry(
            spec,
            "scheduled" if scheduled else "on_demand",
            SourceConnection(
                state, enabled, environment_disabled, active, requirement, health, detail
            ),
        )


FEEDS_OFF = "Live feed collection is switched off on this server (ASE_FEEDS_ENABLED=false)."
_WAITING = frozenset(
    {
        ConnectionState.CONNECTED,
        ConnectionState.IDLE,
        ConnectionState.KEY_UNVERIFIED,
        ConnectionState.DEGRADED,
        ConnectionState.FAILING,
        ConnectionState.BLOCKED_UPSTREAM,
    }
)

_DETAILS = {
    ConnectionState.DISABLED_BY_ENVIRONMENT: (
        "Left out by the operator's feed configuration on this server."
    ),
    ConnectionState.DISABLED_BY_ADMIN: "Switched off by an administrator.",
    ConnectionState.ON_DEMAND: "Queried only when a research run selects it.",
    ConnectionState.NOT_CONFIGURED: "Registered but not running in this process.",
    ConnectionState.KEY_UNVERIFIED: "Credential present; no successful collection yet.",
    ConnectionState.CONNECTED: "Collecting on schedule.",
    ConnectionState.DEGRADED: "Recent collection attempts failed; retrying with backoff.",
    ConnectionState.FAILING: "Paused after repeated failures until an administrator resets it.",
    ConnectionState.IDLE: "Waiting for the first collection.",
}


def _state(
    scheduled: bool,
    active: bool,
    enabled: bool,
    environment_disabled: bool,
    requirement: SourceRequirement | None,
    health: SourceHealth | None,
) -> tuple[ConnectionState, str]:
    """A missing requirement outranks every other reason a source is not collecting."""
    if requirement is not None and requirement.satisfied is False and not requirement.optional:
        keyed = requirement.kind in ("api_key", "credentials")
        return (
            ConnectionState.KEY_MISSING if keyed else ConnectionState.NOT_CONFIGURED,
            requirement.note,
        )
    if environment_disabled:
        state = ConnectionState.DISABLED_BY_ENVIRONMENT
    elif not enabled:
        state = ConnectionState.DISABLED_BY_ADMIN
    elif not scheduled:
        state = ConnectionState.ON_DEMAND
    elif not active or health is None:
        state = ConnectionState.NOT_CONFIGURED
    elif health.blocked_reason:
        return ConnectionState.BLOCKED_UPSTREAM, health.blocked_reason
    else:
        state = _HEALTH_STATES[health.status]
        if state is ConnectionState.IDLE and requirement is not None and requirement.satisfied:
            state = ConnectionState.KEY_UNVERIFIED
    return state, _DETAILS[state]

"""Validated commands for an atomic connection and daily allowance edit."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from ase.domain.errors import InvalidRequest

WorkspaceScope = Literal["global", "team", "user"]
AllowancePreset = Literal["light", "standard", "intensive", "power", "blocked", "inherit"]
PRESET_LIMITS: dict[str, tuple[int, int]] = {
    "light": (50, 100_000),
    "standard": (250, 500_000),
    "intensive": (1000, 2_000_000),
    "power": (2500, 5_000_000),
    "blocked": (0, 0),
}


@dataclass(frozen=True, slots=True)
class WorkspaceModelInput:
    profile_id: UUID | None
    expected_binding_revision: int | None
    expected_profile_revision: int | None
    tested_config_hash: str | None

    def __post_init__(self) -> None:
        if self.profile_id is not None:
            if self.expected_profile_revision is None or self.tested_config_hash is None:
                raise InvalidRequest("Select a successfully tested model before applying it.")
        elif self.expected_binding_revision is None:
            raise InvalidRequest("Reload the current connection before removing an override.")


@dataclass(frozen=True, slots=True)
class WorkspaceAllowanceInput:
    preset: AllowancePreset
    expected_policy_id: UUID | None
    expected_policy_revision: int | None

    def __post_init__(self) -> None:
        if self.preset not in PRESET_LIMITS and self.preset != "inherit":
            raise InvalidRequest("Select a recognised daily allowance preset.")
        if (self.expected_policy_id is None) != (self.expected_policy_revision is None):
            raise InvalidRequest("The expected allowance needs both its identifier and revision.")


@dataclass(frozen=True, slots=True)
class WorkspaceChange:
    scope: WorkspaceScope
    target_id: UUID | None
    model: WorkspaceModelInput | None
    allowance: WorkspaceAllowanceInput | None

    def __post_init__(self) -> None:
        if self.scope not in {"global", "team", "user"}:
            raise InvalidRequest("Select a global, team or personal workspace.")
        if (self.scope == "global") != (self.target_id is None):
            raise InvalidRequest("Only team and personal workspaces require a target.")
        if self.model is None and self.allowance is None:
            raise InvalidRequest("Each workspace edit must change its model or daily allowance.")
        if self.scope == "global" and self.model is not None and self.model.profile_id is None:
            raise InvalidRequest("The global connection cannot be removed.")

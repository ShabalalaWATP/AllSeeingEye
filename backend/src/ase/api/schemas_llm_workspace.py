"""Bounded API contract for atomic AI workspace edits."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.api.schemas_ai_usage import AiUsagePolicyOut
from ase.api.schemas_llm import LlmConnectionOut
from ase.application.admin.llm_workspace import WorkspaceResult
from ase.application.admin.llm_workspace_inputs import (
    AllowancePreset,
    WorkspaceAllowanceInput,
    WorkspaceChange,
    WorkspaceModelInput,
    WorkspaceScope,
)


class LlmWorkspaceModelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: UUID | None
    expected_binding_revision: int | None = Field(default=None, ge=1)
    expected_profile_revision: int | None = Field(default=None, ge=1)
    tested_config_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    def to_input(self) -> WorkspaceModelInput:
        return WorkspaceModelInput(
            self.profile_id,
            self.expected_binding_revision,
            self.expected_profile_revision,
            self.tested_config_hash,
        )


class LlmWorkspaceAllowanceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: AllowancePreset
    expected_policy_id: UUID | None = None
    expected_policy_revision: int | None = Field(default=None, ge=1)

    def to_input(self) -> WorkspaceAllowanceInput:
        return WorkspaceAllowanceInput(
            self.preset, self.expected_policy_id, self.expected_policy_revision
        )


class LlmWorkspaceChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: WorkspaceScope
    target_id: UUID | None = None
    model: LlmWorkspaceModelIn | None = None
    allowance: LlmWorkspaceAllowanceIn | None = None

    def to_input(self) -> WorkspaceChange:
        return WorkspaceChange(
            self.scope,
            self.target_id,
            self.model.to_input() if self.model else None,
            self.allowance.to_input() if self.allowance else None,
        )


class LlmWorkspaceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changes: list[LlmWorkspaceChangeIn] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_targets(self) -> Self:
        if len({(change.scope, change.target_id) for change in self.changes}) != len(self.changes):
            raise ValueError("Each workspace can appear only once in an update.")
        return self


class LlmWorkspaceOut(BaseModel):
    connections: list[LlmConnectionOut]
    policies: list[AiUsagePolicyOut]

    @classmethod
    def from_result(cls, result: WorkspaceResult) -> Self:
        return cls(
            connections=[LlmConnectionOut.from_binding(item) for item in result.connections],
            policies=[AiUsagePolicyOut.from_policy(item) for item in result.policies],
        )

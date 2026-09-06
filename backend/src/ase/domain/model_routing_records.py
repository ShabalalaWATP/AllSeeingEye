"""Strict bounded codec for non-secret, frozen model routing provenance."""

from dataclasses import fields
from datetime import datetime
from math import isfinite
from typing import Any, Literal, cast
from uuid import UUID

from ase.domain.llm import (
    MAX_MODEL_ID_LENGTH,
    MAX_OUTPUT_TOKENS,
    MIN_OUTPUT_TOKENS,
    TEXT_ROLES,
    LlmProvider,
    LlmRole,
    ReasoningEffort,
)
from ase.domain.model_routing import ModelRoutingRecord, RoutedModel


def routing_to_dict(value: ModelRoutingRecord | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "policy": value.policy,
        "destination_team_id": str(value.destination_team_id)
        if value.destination_team_id
        else None,
        "binding_team_id": str(value.binding_team_id) if value.binding_team_id else None,
        "profiles": [
            {
                "role": profile.role.value,
                "profile_id": str(profile.profile_id),
                "profile_revision": profile.profile_revision,
                "model": profile.model,
                "provider": profile.provider.value,
                "reasoning_effort": profile.reasoning_effort.value
                if profile.reasoning_effort
                else None,
                "max_output_tokens": profile.max_output_tokens,
                "temperature": profile.temperature,
                "profile_updated_at": profile.profile_updated_at.isoformat(),
            }
            for profile in value.profiles
        ],
    }


def _uuid(value: Any) -> UUID:
    if type(value) is not str or len(value) != 36:
        raise ValueError("Invalid saved model routing identifier")
    return UUID(value)


def _profile(value: Any) -> RoutedModel:
    names = {item.name for item in fields(RoutedModel)}
    if type(value) is not dict or set(value) not in (names, names - {"provider"}):
        raise ValueError("Invalid saved model settings")
    role = LlmRole(value["role"])
    provider = LlmProvider(value.get("provider", LlmProvider.OPENAI_COMPATIBLE.value))
    model_limit = MAX_MODEL_ID_LENGTH if provider is LlmProvider.BEDROCK else 200
    model, revision, budget = value["model"], value["profile_revision"], value["max_output_tokens"]
    temperature, timestamp = value["temperature"], value["profile_updated_at"]
    if (
        role not in TEXT_ROLES
        or type(model) is not str
        or not 1 <= len(model) <= model_limit
        or type(revision) is not int
        or not 1 <= revision <= 2**31 - 1
        or type(budget) is not int
        or not MIN_OUTPUT_TOKENS <= budget <= MAX_OUTPUT_TOKENS
        or type(temperature) not in {int, float}
        or not isfinite(temperature)
        or not 0 <= temperature <= 2
        or type(timestamp) is not str
        or len(timestamp) > 64
        or "T" not in timestamp
    ):
        raise ValueError("Invalid saved model settings value")
    return RoutedModel(
        role,
        _uuid(value["profile_id"]),
        revision,
        model,
        ReasoningEffort(value["reasoning_effort"])
        if value["reasoning_effort"] is not None
        else None,
        budget,
        float(temperature),
        datetime.fromisoformat(timestamp),
        provider,
    )


def routing_from_dict(value: Any) -> ModelRoutingRecord | None:
    if value is None:
        return None
    if type(value) is not dict or set(value) != {item.name for item in fields(ModelRoutingRecord)}:
        raise ValueError("Invalid saved model routing fields")
    policy = value["policy"]
    profiles = value["profiles"]
    if type(policy) is not str or policy not in {"legacy", "global", "team"}:
        raise ValueError("Invalid saved model routing policy")
    if type(profiles) is not list or not 1 <= len(profiles) <= len(TEXT_ROLES):
        raise ValueError("Invalid saved model routing roles")
    decoded = tuple(_profile(profile) for profile in profiles)
    if len({profile.role for profile in decoded}) != len(decoded):
        raise ValueError("Duplicate saved model routing role")
    destination = (
        _uuid(value["destination_team_id"]) if value["destination_team_id"] is not None else None
    )
    binding = _uuid(value["binding_team_id"]) if value["binding_team_id"] is not None else None
    if (policy == "team" and (binding is None or binding != destination)) or (
        policy != "team" and binding is not None
    ):
        raise ValueError("Invalid saved model routing scope")
    if policy != "legacy" and {profile.role for profile in decoded} != TEXT_ROLES:
        raise ValueError("Incomplete saved assigned model roles")
    return ModelRoutingRecord(
        cast(Literal["legacy", "global", "team"], policy), destination, binding, decoded
    )

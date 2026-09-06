"""Frozen routing history is bounded, typed and free of endpoints and credentials."""

import copy
import json
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.api.schemas_reports import ReportVersionOut
from ase.domain.llm import LlmProvider
from ase.domain.model_routing_records import routing_from_dict, routing_to_dict
from ase.domain.report_records import analysis_to_dict
from report_documents_helpers import document_records
from test_model_routing import binding, profile, routing


async def record():
    configured = profile()
    service, _ = routing([configured], {None: binding(configured)})
    return (await service.snapshot()).provenance


async def test_json_and_typed_response_roundtrip_has_no_provider_or_key():
    value = await record()
    encoded = routing_to_dict(value)
    assert routing_from_dict(json.loads(json.dumps(encoded))) == value
    raw = json.dumps(encoded)
    assert "localhost" not in raw and "encrypted" not in raw and "hint" not in raw
    _, version = document_records(uuid4())
    version.model_routing = value
    assert analysis_to_dict(version)["model_routing"] == encoded
    response = ReportVersionOut.from_version(version).model_dump(mode="json")["model_routing"]
    assert routing_from_dict(response) == value


def test_absent_legacy_metadata_is_not_invented():
    assert routing_from_dict(None) is None
    assert routing_to_dict(None) is None
    _, version = document_records(uuid4())
    assert ReportVersionOut.from_version(version).model_routing is None


@pytest.mark.parametrize(
    "change",
    [
        "extra",
        "policy",
        "profiles",
        "duplicates",
        "partial",
        "scope",
        "false_uuid",
        "profile_extra",
        "role",
        "model",
        "revision",
        "budget",
        "temperature",
        "timestamp",
        "effort",
        "uuid",
    ],
)
async def test_corrupt_or_unbounded_saved_settings_are_rejected(change):
    data = copy.deepcopy(routing_to_dict(await record()))
    if change == "extra":
        data["api_key"] = "injected"
    elif change == "policy":
        data["policy"] = "guessed"
    elif change == "profiles":
        data["profiles"] *= 100
    elif change == "duplicates":
        data["profiles"][1] = data["profiles"][0]
    elif change == "partial":
        data["profiles"] = data["profiles"][:1]
    elif change == "scope":
        data["binding_team_id"] = str(uuid4())
    elif change == "false_uuid":
        data["destination_team_id"] = False
    else:
        key, value = {
            "profile_extra": ("api_key", "injected"),
            "role": ("role", "embeddings"),
            "model": ("model", "x" * 201),
            "revision": ("profile_revision", True),
            "budget": ("max_output_tokens", 0),
            "temperature": ("temperature", float("nan")),
            "timestamp": ("profile_updated_at", 0),
            "effort": ("reasoning_effort", "unknown"),
            "uuid": ("profile_id", "x"),
        }[change]
        data["profiles"][0][key] = value
    with pytest.raises(ValueError):
        routing_from_dict(data)


async def test_legacy_partial_roles_and_team_scope_roundtrip():
    value = await record()
    legacy = replace(value, policy="legacy", profiles=value.profiles[:1])
    assert routing_from_dict(routing_to_dict(legacy)) == legacy
    team_id = uuid4()
    team = replace(value, policy="team", binding_team_id=team_id, destination_team_id=team_id)
    assert routing_from_dict(routing_to_dict(team)) == team


async def test_provider_is_frozen_and_legacy_absence_defaults_to_openai_compatible():
    configured = profile(provider=LlmProvider.BEDROCK)
    service, _ = routing([configured], {None: binding(configured)})
    frozen = (await service.snapshot()).provenance
    assert all(item.provider is LlmProvider.BEDROCK for item in frozen.profiles)
    data = routing_to_dict(frozen)
    assert routing_from_dict(json.loads(json.dumps(data))) == frozen
    assert all(row["provider"] == "bedrock" for row in data["profiles"])
    for row in data["profiles"]:
        row.pop("provider")
    assert all(
        row.provider is LlmProvider.OPENAI_COMPATIBLE for row in routing_from_dict(data).profiles
    )
    data["profiles"][0]["provider"] = "unknown"
    with pytest.raises(ValueError):
        routing_from_dict(data)


async def test_long_native_model_identifier_roundtrips_frozen_provenance():
    identifier = "arn:aws:bedrock:eu-west-2:123456789012:inference-profile/" + "a" * 1700
    configured = profile(model=identifier, provider=LlmProvider.BEDROCK)
    service, _ = routing([configured], {None: binding(configured)})
    frozen = (await service.snapshot()).provenance
    data = routing_to_dict(frozen)
    assert routing_from_dict(data) == frozen
    _, version = document_records(uuid4())
    version.model_routing = frozen
    assert ReportVersionOut.from_version(version).model_routing.profiles[0].model == identifier
    data["profiles"][0]["model"] = "x" * 2049
    with pytest.raises(ValueError):
        routing_from_dict(data)

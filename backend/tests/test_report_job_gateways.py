"""Actual per-call role profiles, including ambiguous legacy configurations."""

import json
from dataclasses import fields, replace
from uuid import UUID

import pytest

from ase.application.model_routing import RoleProfiles
from ase.application.ports.web_search import WebSearchRequest, WebSearchResult
from ase.application.report_jobs.budget import JobBudgetExhausted, JobInterrupted, output_used
from ase.container.report_job_gateways import bind_report_job_gateways
from ase.domain.llm import TEXT_ROLES, LlmProvider, LlmRole, ReasoningEffort
from ase.domain.model_routing import ModelRoutingRecord
from report_job_budget_helpers import REQUEST, RESPONSE, Gateway, Ledger, row
from report_job_snapshot_helpers import fixture_job

BASE = "https://api.openai.com/v1"
FIRST_ID = UUID("6a156b03-b426-48ca-a5aa-4b212b5cf53d")
SECOND_ID = UUID("392229cc-b0c2-49a7-b9fb-76dce290d270")
FIRST = replace(
    fixture_job().profile,
    id=FIRST_ID,
    model="first-model",
    base_url=BASE,
    api_key_encrypted="private-first-secret",
    roles=TEXT_ROLES,
    max_output_tokens=32000,
)
SECOND = replace(
    FIRST, id=SECOND_ID, model="second-model", api_key_encrypted="private-second-secret"
)
WEB_REQUEST = WebSearchRequest("private-question", 16000, ReasoningEffort.MAX)
WEB_RESPONSE = WebSearchResult("private-output", (), (), "first-model", 1, 0, 1, 2)


class Cipher:
    error = False

    def decrypt(self, value):
        if self.error:
            raise ValueError("private-cipher-failure")
        return "decrypted-" + value


def routing_for(mapping):
    return RoleProfiles(
        ModelRoutingRecord("legacy", None, None, ()),
        tuple(
            (role, tuple((field.name, getattr(profile, field.name)) for field in fields(profile)))
            for role, profile in mapping.items()
        ),
    )


async def bind(ledger, mapping, *, cipher=None):
    llm = Gateway(ledger)
    web = Gateway(ledger, WEB_RESPONSE)
    bound = await bind_report_job_gateways(
        routing_for(mapping), cipher or Cipher(), llm, web, ledger.budget()
    )
    return (*bound, llm, web)


async def invoke(gateway, profile=FIRST, request=REQUEST, *, key=None, model=None, base=None):
    return await gateway.complete(
        base or profile.base_url,
        key or Cipher().decrypt(profile.api_key_encrypted),
        model or profile.model,
        request,
    )


async def test_direction_and_assessment_calls_record_their_actual_frozen_profile():
    ledger = Ledger()
    gateway, _, llm, _ = await bind(ledger, {LlmRole.DIRECTION: FIRST, LlmRole.ASSESSMENT: SECOND})
    assert await invoke(gateway, FIRST) is RESPONSE
    assert await invoke(gateway, SECOND) is RESPONSE
    assert [entry["profile_id"] for entry in ledger.payload["calls"]] == [
        str(FIRST_ID),
        str(SECOND_ID),
    ]
    assert llm.calls[0][3] is REQUEST and llm.calls[1][3] is REQUEST
    assert "private-" not in json.dumps(ledger.payload)


async def test_identical_config_without_declared_profile_fails_before_spending():
    ledger = Ledger()
    gateway, _, _, _ = await bind(
        ledger, {LlmRole.DIRECTION: FIRST, LlmRole.ASSESSMENT: replace(FIRST, id=SECOND_ID)}
    )
    with pytest.raises(JobInterrupted):
        await invoke(gateway)
    assert not ledger.writes


async def test_declared_profile_disambiguates_identical_config_without_changing_request():
    ledger = Ledger()
    gateway, _, llm, _ = await bind(
        ledger, {LlmRole.DIRECTION: FIRST, LlmRole.ASSESSMENT: replace(FIRST, id=SECOND_ID)}
    )
    request = replace(REQUEST, profile_id=SECOND_ID)
    await invoke(gateway, request=request)
    assert ledger.payload["calls"][0]["profile_id"] == str(SECOND_ID)
    assert output_used(ledger.payload) == RESPONSE.completion_tokens
    assert llm.calls[0][3] is request


async def test_declared_profile_cannot_claim_another_profiles_settings_or_identity():
    ledger = Ledger()
    gateway, _, llm, _ = await bind(ledger, {LlmRole.DIRECTION: FIRST, LlmRole.ASSESSMENT: SECOND})
    for profile_id in (SECOND_ID, UUID(int=0)):
        with pytest.raises(JobInterrupted):
            await invoke(gateway, request=replace(REQUEST, profile_id=profile_id))
    assert not llm.calls and not ledger.writes


async def test_shared_profile_serving_all_roles_is_uniquely_attributed():
    ledger = Ledger()
    gateway, _, _, _ = await bind(ledger, dict.fromkeys(TEXT_ROLES, FIRST))
    await invoke(gateway)
    assert ledger.payload["calls"][0]["profile_id"] == str(FIRST_ID)


async def test_equal_model_settings_with_different_keys_remain_distinguishable():
    ledger = Ledger()
    second = replace(SECOND, model=FIRST.model)
    gateway, _, _, _ = await bind(ledger, {LlmRole.DIRECTION: FIRST, LlmRole.ASSESSMENT: second})
    await invoke(gateway, second)
    assert ledger.payload["calls"][0]["profile_id"] == str(SECOND_ID)


@pytest.mark.parametrize(
    "changes",
    [
        {"base": "https://different.invalid/v1"},
        {"model": "different-model"},
        {"key": "private-wrong-key"},
        {"request": replace(REQUEST, provider=LlmProvider.BEDROCK)},
        {"request": replace(REQUEST, reasoning_effort=ReasoningEffort.HIGH)},
        {"request": replace(REQUEST, temperature=0.7)},
        {"request": replace(REQUEST, temperature=True)},
        {"request": replace(REQUEST, temperature=float("nan"))},
        {"request": replace(REQUEST, max_output_tokens=32001)},
        {"request": replace(REQUEST, max_output_tokens=0)},
        {"request": replace(REQUEST, max_output_tokens=True)},
    ],
)
async def test_mismatched_provider_settings_fail_before_reservation_or_network(changes):
    ledger = Ledger()
    gateway, _, llm, _ = await bind(ledger, {LlmRole.ASSESSMENT: FIRST})
    with pytest.raises(JobInterrupted) as error:
        await invoke(gateway, **changes)
    assert "private-" not in str(error.value)
    assert not ledger.writes and not llm.calls


async def test_smaller_per_stage_output_is_allowed_but_cannot_exceed_profile_budget():
    ledger = Ledger()
    profile = replace(FIRST, max_output_tokens=8000)
    gateway, _, llm, _ = await bind(ledger, {LlmRole.ASSESSMENT: profile})
    request = replace(REQUEST, max_output_tokens=2000)
    await invoke(gateway, profile, request)
    with pytest.raises(JobInterrupted):
        await invoke(gateway, profile, replace(REQUEST, max_output_tokens=8001))
    assert len(llm.calls) == 1 and llm.calls[0][3] is request


async def test_bedrock_profile_is_not_changed_or_sent_to_a_different_gateway():
    ledger = Ledger()
    profile = replace(FIRST, provider=LlmProvider.BEDROCK, base_url="https://bedrock.invalid")
    gateway, _, llm, _ = await bind(ledger, {LlmRole.ASSESSMENT: profile})
    request = replace(REQUEST, provider=LlmProvider.BEDROCK)
    await invoke(gateway, profile, request)
    assert llm.calls[0][0] == profile.base_url and llm.calls[0][3] is request
    assert ledger.payload["calls"][0]["profile_id"] == str(FIRST_ID)


async def test_unreadable_credential_fails_safely_without_model_or_ledger_call():
    ledger, cipher = Ledger(), Cipher()
    cipher.error = True
    gateway, _, llm, _ = await bind(ledger, {LlmRole.ASSESSMENT: FIRST}, cipher=cipher)
    with pytest.raises(JobInterrupted) as error:
        await invoke(gateway)
    assert "private-" not in str(error.value)
    assert not llm.calls and not ledger.writes


async def test_web_search_uses_direction_profile_even_when_profiles_are_identical():
    ledger = Ledger()
    _, gateway, _, web = await bind(
        ledger, {LlmRole.DIRECTION: FIRST, LlmRole.ASSESSMENT: replace(FIRST, id=SECOND_ID)}
    )
    result = await gateway.search(
        Cipher().decrypt(FIRST.api_key_encrypted), FIRST.model, WEB_REQUEST
    )
    assert result is WEB_RESPONSE
    assert ledger.payload["calls"][0]["profile_id"] == str(FIRST_ID)
    assert web.calls[0][3] is WEB_REQUEST


@pytest.mark.parametrize(
    "profile,model,key,model_request",
    [
        (FIRST, SECOND.model, None, WEB_REQUEST),
        (FIRST, FIRST.model, "private-wrong-key", WEB_REQUEST),
        (FIRST, FIRST.model, None, replace(WEB_REQUEST, reasoning_effort=ReasoningEffort.HIGH)),
        (FIRST, FIRST.model, None, replace(WEB_REQUEST, max_output_tokens=16001)),
        (replace(FIRST, max_output_tokens=8000), FIRST.model, None, WEB_REQUEST),
        (replace(FIRST, provider=LlmProvider.BEDROCK), FIRST.model, None, WEB_REQUEST),
        (replace(FIRST, base_url="https://compatible.invalid/v1"), FIRST.model, None, WEB_REQUEST),
    ],
)
async def test_web_settings_must_match_native_direction_profile(profile, model, key, model_request):
    ledger = Ledger()
    _, gateway, _, web = await bind(ledger, {LlmRole.DIRECTION: profile})
    with pytest.raises(JobInterrupted):
        await gateway.search(
            key or Cipher().decrypt(profile.api_key_encrypted), model, model_request
        )
    assert not web.calls and not ledger.writes


async def test_missing_optional_direction_does_not_prevent_assessment():
    ledger = Ledger()
    gateway, web, _, _ = await bind(ledger, {LlmRole.ASSESSMENT: FIRST})
    await invoke(gateway)
    with pytest.raises(JobInterrupted):
        await web.search("test", FIRST.model, WEB_REQUEST)
    assert len(ledger.payload["calls"]) == 1


async def test_inactive_or_unpermitted_profiles_cannot_be_used():
    ledger = Ledger()
    gateway, web, llm, actual_web = await bind(
        ledger,
        {
            LlmRole.ASSESSMENT: replace(FIRST, enabled=False),
            LlmRole.DIRECTION: replace(FIRST, roles=frozenset()),
        },
    )
    with pytest.raises(JobInterrupted):
        await invoke(gateway)
    with pytest.raises(JobInterrupted):
        await web.search("test", FIRST.model, WEB_REQUEST)
    assert not ledger.writes and not llm.calls and not actual_web.calls


async def test_profile_attribution_forks_share_lifetime_capacity_and_access_check():
    ledger = Ledger()
    ledger.payload["calls"] = [row(completion=None)] * 8
    gateway, _, llm, _ = await bind(ledger, {LlmRole.ASSESSMENT: FIRST})
    with pytest.raises(JobBudgetExhausted):
        await invoke(gateway)
    assert not llm.calls and ledger.checks == 1


@pytest.mark.parametrize(
    "schema", ["research_plan", "research_replan", "research_continuation", "query_translation"]
)
async def test_existing_deterministic_planning_controls_are_preserved(schema):
    ledger = Ledger()
    gateway, _, llm, _ = await bind(ledger, {LlmRole.DIRECTION: FIRST})
    request = replace(REQUEST, profile_id=FIRST_ID, schema_name=schema, temperature=0)
    await invoke(gateway, request=request)
    assert llm.calls[0][3] is request and ledger.payload["calls"][0]["profile_id"] == str(FIRST_ID)
    with pytest.raises(JobInterrupted):
        await invoke(gateway, request=replace(request, temperature=FIRST.temperature))

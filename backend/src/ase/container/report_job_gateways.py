"""Attribute calls to immutable role profiles without changing provider requests."""

import math
import secrets

from ase.adapters.llm.openai_responses import OPENAI_BASE
from ase.application.model_routing import RoleProfiles
from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.ports.web_search import (
    MAX_WEB_OUTPUT_TOKENS,
    WebSearchGateway,
    WebSearchRequest,
    WebSearchResult,
)
from ase.application.report_jobs.budget import JobInterrupted, ReportCallBudget
from ase.application.report_jobs.model_calls import BudgetedLlmGateway, BudgetedWebSearchGateway
from ase.domain.llm import (
    MAX_OUTPUT_TOKENS,
    TEXT_ROLES,
    LlmProfile,
    LlmProvider,
    LlmRequest,
    LlmResult,
    LlmRole,
)

MISMATCH = "The report model request does not match its frozen configuration."
ZERO_TEMPERATURE_SCHEMAS = frozenset(
    {"research_plan", "research_replan", "research_continuation", "query_translation"}
)


def _output_matches(value: int, profile: LlmProfile, ceiling: int) -> bool:
    return type(value) is int and 1 <= value <= min(profile.max_output_tokens, ceiling)


def _key_matches(cipher: SecretCipher, profile: LlmProfile, api_key: str) -> bool:
    try:
        expected = cipher.decrypt(profile.api_key_encrypted)
        return secrets.compare_digest(expected.encode(), api_key.encode())
    except Exception:
        raise JobInterrupted(MISMATCH) from None


def _request_matches(base_url: str, model: str, request: LlmRequest, profile: LlmProfile) -> bool:
    temperature = 0 if request.schema_name in ZERO_TEMPERATURE_SCHEMAS else profile.temperature
    return (
        base_url == profile.base_url
        and model == profile.model
        and request.provider == profile.provider
        and request.reasoning_effort == profile.reasoning_effort
        and type(request.temperature) in (int, float)
        and math.isfinite(request.temperature)
        and request.temperature == temperature
        and _output_matches(request.max_output_tokens, profile, MAX_OUTPUT_TOKENS)
    )


class _RoutedLlmGateway:
    def __init__(
        self,
        profiles: tuple[LlmProfile, ...],
        cipher: SecretCipher,
        gateway: LlmGateway,
        budget: ReportCallBudget,
    ) -> None:
        self._profiles, self._cipher = profiles, cipher
        self._gateway, self._budget = gateway, budget

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        matching_ids = {
            profile.id
            for profile in self._profiles
            if (request.profile_id is None or request.profile_id == profile.id)
            and _request_matches(base_url, model, request, profile)
            and _key_matches(self._cipher, profile, api_key)
        }
        if len(matching_ids) != 1:
            raise JobInterrupted(MISMATCH)
        # Identical legacy profiles need the stage's explicit internal profile ID.
        profile_id = next(iter(matching_ids))
        gateway = BudgetedLlmGateway(self._gateway, self._budget.with_profile(profile_id))
        return await gateway.complete(base_url, api_key, model, request)


class _RoutedWebGateway:
    def __init__(
        self,
        direction: LlmProfile | None,
        cipher: SecretCipher,
        gateway: WebSearchGateway,
        budget: ReportCallBudget,
    ) -> None:
        self._direction, self._cipher = direction, cipher
        self._gateway, self._budget = gateway, budget

    async def search(self, api_key: str, model: str, request: WebSearchRequest) -> WebSearchResult:
        profile = self._direction
        if (
            profile is None
            or profile.provider is not LlmProvider.OPENAI_COMPATIBLE
            or profile.base_url.rstrip("/") != OPENAI_BASE
            or model != profile.model
            or request.reasoning_effort != profile.reasoning_effort
            or not _output_matches(request.max_output_tokens, profile, MAX_WEB_OUTPUT_TOKENS)
            or not _key_matches(self._cipher, profile, api_key)
        ):
            raise JobInterrupted(MISMATCH)
        gateway = BudgetedWebSearchGateway(self._gateway, self._budget.with_profile(profile.id))
        return await gateway.search(api_key, model, request)


async def bind_report_job_gateways(
    routing: RoleProfiles,
    cipher: SecretCipher,
    gateway: LlmGateway,
    web_gateway: WebSearchGateway,
    budget: ReportCallBudget,
) -> tuple[LlmGateway, WebSearchGateway]:
    """Hold only private per-run profile copies; ledger records contain no secrets."""
    profiles = []
    for role in sorted(TEXT_ROLES):
        profile = await routing.profile_for(role)
        if profile is not None and profile.allows(role):
            profiles.append(profile)
    direction = await routing.profile_for(LlmRole.DIRECTION)
    if direction is not None and not direction.allows(LlmRole.DIRECTION):
        direction = None
    return (
        _RoutedLlmGateway(tuple(profiles), cipher, gateway, budget),
        _RoutedWebGateway(direction, cipher, web_gateway, budget),
    )

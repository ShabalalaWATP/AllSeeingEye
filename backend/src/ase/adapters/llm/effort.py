"""Cap reasoning effort for mechanical work at the single point every call passes through.

Every provider request reaches a gateway with the ``schema_name`` its builder chose, so
one decorator can lower effort for mechanical purposes without touching the analytical
call sites.  Report, direction, devil's advocacy and Ask Eye requests pass through
unchanged, and recorded model provenance still reflects the profile the operator set.
"""

from __future__ import annotations

from dataclasses import replace

from ase.application.ports.llm import LlmGateway
from ase.domain.llm import LlmRequest, LlmResult
from ase.domain.reasoning import ReasoningEffortPolicy


class MechanicalEffortGateway:
    """Delegates the call; rewrites only the reasoning effort of capped purposes."""

    def __init__(self, gateway: LlmGateway, policy: ReasoningEffortPolicy) -> None:
        self._gateway = gateway
        self._policy = policy

    @property
    def policy(self) -> ReasoningEffortPolicy:
        return self._policy

    def apply(self, request: LlmRequest) -> LlmRequest:
        effort = self._policy.effort_for(request.schema_name, request.reasoning_effort)
        if effort is request.reasoning_effort:
            return request
        return replace(request, reasoning_effort=effort)

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        return await self._gateway.complete(base_url, api_key, model, self.apply(request))

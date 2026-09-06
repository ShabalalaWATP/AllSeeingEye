"""Dispatch explicitly configured protocols without credential or provider fallback."""

from ase.adapters.llm.bedrock import BedrockConverseGateway
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.application.ports.llm import LlmGatewayError
from ase.domain.llm import LlmProvider, LlmRequest, LlmResult


class RoutingLlmGateway:
    def __init__(
        self, openai_gateway: OpenAiCompatibleGateway, bedrock_gateway: BedrockConverseGateway
    ) -> None:
        self.openai = openai_gateway
        self.bedrock = bedrock_gateway

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        if request.provider == LlmProvider.BEDROCK:
            return await self.bedrock.complete(base_url, api_key, model, request)
        if request.provider == LlmProvider.OPENAI_COMPATIBLE:
            return await self.openai.complete(base_url, api_key, model, request)
        raise LlmGatewayError("The configured model provider is unsupported.")

    async def list_models(self, base_url: str, api_key: str) -> tuple[str, ...]:
        return await self.openai.list_models(base_url, api_key)

    async def aclose(self) -> None:
        try:
            await self.openai.aclose()
        finally:
            await self.bedrock.aclose()

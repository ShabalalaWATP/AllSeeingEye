"""Presentation-only AI authorship, without claiming source or model authenticity."""

from dataclasses import dataclass
from typing import Literal
from unicodedata import category

Provider = Literal["openai_compatible", "bedrock", "unknown"]
AI_LABEL = "AI-assisted assessment"
AI_SCOPE = "Assessment text; source evidence and human annotations are not classified."


@dataclass(frozen=True, slots=True)
class AiDisclosure:
    model: str
    provider: Provider = "unknown"
    assessment_generated: bool = True

    def __post_init__(self) -> None:
        if (
            not isinstance(self.model, str)
            or len(self.model) > 2_048
            or any(category(char).startswith("C") for char in self.model)
            or self.provider not in {"openai_compatible", "bedrock", "unknown"}
            or type(self.assessment_generated) is not bool
        ):
            raise ValueError("Invalid AI disclosure provenance")

    @property
    def provider_label(self) -> str:
        return {
            "openai_compatible": "OpenAI-compatible connector (host not recorded)",
            "bedrock": "Amazon Bedrock",
            "unknown": "Not recorded",
        }[self.provider]

    @property
    def statement(self) -> str:
        if not self.assessment_generated:
            return (
                "No AI assessment was generated. "
                "This version contains an application-written gap notice."
            )
        return (
            f"{AI_LABEL}. Produced with AI assistance. "
            f"Model: {self.model or 'Not recorded'}. Provider: {self.provider_label}."
        )

    @property
    def footer(self) -> str:
        if not self.assessment_generated:
            return "No AI assessment generated | Application-written gap notice"
        model = self.model or "Not recorded"
        if len(model) > 50:
            model = model[:47] + "... (full model at title)"
        provider = (
            "OpenAI-compatible (host unknown)"
            if self.provider == "openai_compatible"
            else self.provider_label
        )
        return f"{AI_LABEL} | Model: {model} | Provider: {provider}"

    def metadata(self) -> dict[str, str]:
        return {
            "ase:ai-generated": "true" if self.assessment_generated else "false",
            "ase:ai-model": self.model,
            "ase:ai-provider": self.provider,
            "ase:ai-scope": AI_SCOPE,
        }

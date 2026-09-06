"""The real application Producer with synthetic in-memory inputs and bounded model calls."""

import hashlib
import json
import secrets
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ase.adapters.security.cipher import FernetCipher
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.llm import LlmGateway, LlmGatewayError
from ase.application.reports.production import Job, Producer
from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import template_for
from ase.domain.llm import LlmProfile, LlmRequest, LlmResult, LlmRole, LlmUsage, normalise_base_url
from ase.domain.report_records import (
    analysis_to_dict,
    body_to_dict,
    findings_to_list,
    quality_to_dict,
)
from ase.domain.research import ResearchMode, ResearchQuery
from ase.domain.users import Role, User
from evaluations.casebook import EvaluationCase
from evaluations.metrics import deterministic_metrics
from evaluations.replay import ResearchReplay


class EvaluationProfile(BaseModel):
    """Public settings copied from an app profile, never its encrypted key or operator DB."""

    model_config = ConfigDict(extra="forbid")
    name: str = Field(default="Evaluation profile", min_length=1, max_length=80)
    base_url: str
    model: str = Field(min_length=1, max_length=120)
    max_output_tokens: int = Field(default=4000, ge=64, le=32000)
    temperature: float = Field(default=0.0, ge=0, le=2)
    direction: bool = False
    advocacy: bool = False
    research_mode: ResearchMode | None = None
    research_languages: tuple[str, ...] = ("en",)

    @field_validator("research_languages")
    @classmethod
    def language_codes(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        # Reuse the production language contract without maintaining a second regex.
        now = datetime.now(UTC)
        return ResearchQuery("Evaluation", now - timedelta(hours=1), now, values).languages

    @field_validator("base_url")
    @classmethod
    def safe_url(cls, value: str) -> str:
        url = normalise_base_url(value)
        if urlsplit(url).query or urlsplit(url).fragment:
            raise ValueError("Evaluation endpoint URLs must not contain queries or fragments.")
        return url


class RecordingGateway:
    def __init__(self, gateway: LlmGateway, max_calls: int) -> None:
        self.gateway = gateway
        self.max_calls = max_calls
        self.records: list[dict[str, Any]] = []

    async def complete(
        self, base_url: str, api_key: str, model: str, request: LlmRequest
    ) -> LlmResult:
        if len(self.records) >= self.max_calls:
            raise LlmGatewayError("Evaluation model-call budget exhausted.")
        messages = [asdict(message) for message in request.messages]
        record: dict[str, Any] = {
            "schema_name": request.schema_name,
            "requested_model": model,
            "max_output_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "messages": messages,
            "prompt_sha256": hashlib.sha256(
                json.dumps(messages, sort_keys=True).encode()
            ).hexdigest(),
        }
        self.records.append(record)
        try:
            result = await self.gateway.complete(base_url, api_key, model, request)
        except LlmGatewayError as exc:
            record["error"] = str(exc)
            raise
        record.update(asdict(result))
        return result


class MemoryUsage:
    def __init__(self) -> None:
        self.entries: list[LlmUsage] = []

    async def add(self, usage: LlmUsage) -> None:
        self.entries.append(usage)

    async def list_recent(self, limit: int) -> list[LlmUsage]:
        return list(reversed(self.entries[-limit:])) if limit > 0 else []


async def evaluate_case(
    case: EvaluationCase,
    configuration: EvaluationProfile,
    gateway: RecordingGateway,
    api_key: str,
) -> dict[str, Any]:
    store = InMemoryEventStore()
    replay = ResearchReplay(case) if configuration.research_mode else None
    if replay is None:
        store.upsert(case.graded_events())
    cipher = FernetCipher(secrets.token_urlsafe(32))
    roles = {LlmRole.ASSESSMENT}
    if configuration.direction:
        roles.add(LlmRole.DIRECTION)
    if configuration.advocacy:
        roles.add(LlmRole.DEVIL)
    profile = LlmProfile(
        id=uuid4(),
        name=configuration.name,
        base_url=configuration.base_url,
        model=configuration.model,
        api_key_encrypted=cipher.encrypt(api_key),
        api_key_hint="",
        roles=frozenset(roles),
        max_output_tokens=configuration.max_output_tokens,
        temperature=configuration.temperature,
        enabled=True,
        created_at=case.as_of,
        updated_at=case.as_of,
    )
    actor = User(
        id=uuid4(),
        email="evaluation@example.invalid",
        display_name="Evaluation fixture",
        role=Role.ADMIN,
        is_active=True,
        password_hash=None,
        failed_login_count=0,
        last_failed_at=None,
        locked_until=None,
        created_at=case.as_of,
        last_login_at=None,
    )
    usage = MemoryUsage()
    producer = Producer(
        store=store,
        source_profiles=case.source_profiles(),
        cipher=cipher,
        gateway=gateway,
        usage=usage,
        research=replay.collection if replay else None,
        private_store_factory=InMemoryEventStore if replay else None,
    )
    template = template_for("ask" if configuration.direction else "intrep")
    request = ReportRequest(
        template.id,
        question=case.question,
        window_hours=case.window_hours,
        devils_advocacy=configuration.advocacy,
        research_mode=configuration.research_mode,
        research_languages=configuration.research_languages,
    )
    job = Job(
        actor,
        template,
        request,
        profile,
        case.as_of,
        timedelta(hours=case.window_hours),
        case.title,
        {"evaluation_case": case.id, "question": case.question},
        None,
    )

    async def profile_for(role: LlmRole) -> LlmProfile | None:
        return profile if profile.allows(role) else None

    start = len(gateway.records)
    version = await producer.produce(job, profile_for)
    report = {
        "status": version.status.value,
        "body": body_to_dict(version.body),
        "evidence": [asdict(item) for item in version.evidence],
        "quality": quality_to_dict(version.quality),
        "findings": findings_to_list(version.findings),
        "analysis": analysis_to_dict(version),
        "markdown": version.markdown,
        "model": version.model,
        "attempts": version.attempts,
        "prompt_tokens": version.prompt_tokens,
        "completion_tokens": version.completion_tokens,
        "latency_ms": version.latency_ms,
        "model_calls": gateway.records[start:],
    }
    metrics = deterministic_metrics(case, report)
    if replay:
        # Labels can identify different events after the challenge redraft. Comparing
        # every raw answer to the final packet would conceal or invent citation errors.
        metrics["raw_citation_reference_validity"] = {
            "numerator": 0,
            "denominator": 0,
            "value": None,
        }
        metrics["raw_citation_reference_validity_limitation"] = (
            "Not scored for replay: labels can change between initial and final drafts. "
            "Review each recorded answer against its own recorded prompt."
        )
    return {
        "case_id": case.id,
        "case_sha256": case.fingerprint,
        "reference": case.reference.model_dump(mode="json"),
        "report": report,
        "deterministic": metrics,
        "collection_evaluation": replay.result() if replay else {"kind": "fixed_packet"},
    }

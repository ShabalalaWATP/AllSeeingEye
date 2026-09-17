"""Bounded section calls, saved completion and deterministic subdivision on exhaustion."""

import asyncio
import math
import time
from collections.abc import Sequence
from copy import deepcopy
from typing import Any, NoReturn

from ase.application.ports.llm import LlmGateway, LlmGatewayError, LlmTokenBudgetExhausted
from ase.application.ports.section_checkpoints import SectionCheckpoints
from ase.application.reports.drafting import Draft, no_evidence_draft
from ase.application.reports.sections.assembly import assemble
from ase.application.reports.sections.checkpoints import metadata, read_body, write_state
from ase.application.reports.sections.contracts import (
    TOPIC_SCHEMA,
    decode,
    validate_step,
)
from ase.application.reports.sections.outcomes import SectionIncomplete, StepExhausted
from ase.application.reports.sections.plan_selection import select_plan
from ase.application.reports.sections.planning import (
    MAX_TOPIC_LEAVES,
    Topic,
    split_topic,
)
from ase.application.reports.sections.prompts import PromptContext
from ase.application.reports.sections.quality import (
    project_requirement_coverage,
    requirement_support_from_topics,
)
from ase.application.reports.sections.synthesis import collect_synthesis
from ase.application.reports.sections.synthesis_contracts import (
    SCHEMA_NAMES,
    schema_for,
    validate_part,
)
from ase.application.reports.templates import Template
from ase.domain.direction import Direction
from ase.domain.evidence import EvidenceItem, QualityOfInformation
from ase.domain.llm import MAX_OUTPUT_TOKENS, LlmMessage, LlmProfile, LlmRequest
from ase.domain.reports import KeyJudgement, ReportHeader
from ase.domain.research_brief_values import IntelligenceRequirement
from ase.domain.validation import validate_body


class _Runner:
    def __init__(
        self,
        gateway: LlmGateway,
        profile: LlmProfile,
        api_key: str,
        context: PromptContext,
        checkpoints: SectionCheckpoints,
        digest: str,
    ) -> None:
        self.gateway, self.profile, self.api_key = gateway, profile, api_key
        self.context, self.checkpoints = context, checkpoints
        self.draft = Draft(model=profile.model)
        self.eeis = (
            frozenset(row.id for row in context.requirements)
            if context.requirements
            else frozenset(f"EEI-{index}" for index in range(1, len(context.direction.eeis) + 1))
            if context.direction
            else frozenset()
        )
        self.digest = digest
        self.research_mode = context.header.scope.get("research_mode")
        self.completed: list[tuple[Topic, dict[str, Any]]] = []
        self.leaves = 0

    async def run(self, topics: tuple[Topic, ...]) -> Draft:
        self.leaves = len(topics)
        for topic in topics:
            await self.topic(topic)
        expected = metadata(None, tuple(item.label for item in self.context.evidence))
        if not any(body["reporting"] for _, body in self.completed) or not any(
            body["assessment"] for _, body in self.completed
        ):
            await self.pause(expected, "insufficient_evidence")
        try:
            synthesis = await collect_synthesis(
                self.checkpoints,
                self.digest,
                expected,
                self.eeis,
                self.draft,
                call=self.synthesis_call,
                pause=self.pause,
                previous_exists=bool(self.context.previous),
                research_mode=self.research_mode,
            )
            raw = assemble(
                self.completed,
                synthesis,
                self.context.direction,
                requirements=self.context.requirements,
            )
        except (ValueError, TypeError, RecursionError):
            await self.pause(expected, "invalid_synthesis")
        checked = validate_body(
            raw,
            frozenset(expected["evidence_labels"]),
            {},
            previous_exists=bool(self.context.previous),
            evidence_items=self.context.evidence,
        )
        self.draft.body = checked.body
        self.draft.supported_requirements = requirement_support_from_topics(
            self.completed,
            requirements=self.context.requirements,
            direction=self.context.direction,
            judgements=synthesis,
        )
        self.draft.findings.extend(checked.findings)
        if not checked.passed:
            await self.pause(expected, "invalid_synthesis")
        await write_state(self.checkpoints, self.digest, expected, "completed", body=synthesis)
        return self.draft

    async def synthesis_call(
        self,
        expected: dict[str, Any],
        *,
        part: str,
        repair: bool,
        judgements: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return await self.call(None, expected, part=part, repair=repair, judgements=judgements)

    async def topic(self, topic: Topic) -> None:
        expected = metadata(topic, topic.evidence_labels)
        saved = await self.checkpoints.load(self.digest, topic.id)
        if saved and saved.status == "completed":
            try:
                body = read_body(saved, expected, self.eeis)
            except (ValueError, TypeError, RecursionError):
                await self.pause(expected, "invalid_checkpoint")
                return
            self.completed.append((topic, body))
            return
        if saved and saved.status == "running":
            raise SectionIncomplete(topic.id, "interrupted", self.draft)
        if saved and (saved.status == "split" or saved.reason == "token_budget_exhausted"):
            await self.subdivide(
                topic, expected, saved.payload if saved.status == "split" else None
            )
            return
        try:
            body = await self.call(topic, expected, repair=bool(saved))
        except StepExhausted:
            await self.subdivide(topic, expected)
            return
        await write_state(self.checkpoints, self.digest, expected, "completed", body=body)
        self.completed.append((topic, body))

    async def subdivide(
        self,
        topic: Topic,
        expected: dict[str, Any],
        saved: dict[str, Any] | None = None,
    ) -> None:
        children = split_topic(topic)
        if children is None or self.leaves >= MAX_TOPIC_LEAVES:
            await self.pause(expected, "token_budget_exhausted")
            return
        ids = tuple(child.id for child in children)
        if saved is not None and saved != {**expected, "children": list(ids)}:
            await self.pause(expected, "invalid_checkpoint")
        self.leaves += 1
        await write_state(self.checkpoints, self.digest, expected, "split", children=ids)
        for child in children:
            await self.topic(child)

    async def pause(self, expected: dict[str, Any], reason: str) -> NoReturn:
        await write_state(self.checkpoints, self.digest, expected, "incomplete", reason=reason)
        raise SectionIncomplete(str(expected["id"]), reason, self.draft)

    def account(self, model: Any, prompt: Any, completion: Any, elapsed: float) -> None:
        if (
            isinstance(model, str)
            and 0 < len(model) <= 2048
            and not any(ord(c) < 32 for c in model)
        ):
            self.draft.model = model
        for name, count in (("prompt_tokens", prompt), ("completion_tokens", completion)):
            if type(count) is int and 0 <= count <= 2**31 - 1:
                setattr(self.draft, name, (getattr(self.draft, name) or 0) + count)
        if math.isfinite(elapsed) and elapsed >= 0:
            self.draft.latency_ms += elapsed * 1000

    async def call(
        self,
        topic: Topic | None,
        expected: dict[str, Any],
        *,
        repair: bool = False,
        part: str | None = None,
        judgements: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            messages = self.context.messages(
                topic,
                [{"section_id": row.id, "body": body} for row, body in self.completed],
                synthesis_step=part,
                judgements=judgements,
                coverage=project_requirement_coverage(
                    self.completed,
                    requirements=self.context.requirements,
                    direction=self.context.direction,
                    judgements=judgements,
                )
                if part is not None
                else (),
            )
        except (ValueError, TypeError):
            await self.pause(expected, "input_limit")
        if repair:
            messages += (
                LlmMessage(
                    "user",
                    "The previous step was incomplete or failed validation. Recheck the exact "
                    "schema, evidence IDs, assumptions and required doctrine rules. "
                    "Return only the corrected fields for this step.",
                ),
            )
        schema = deepcopy(TOPIC_SCHEMA)
        if part is not None:
            retained_gaps = {
                (gap["eei"], gap["text"].strip().casefold())
                for _, body in self.completed
                for gap in body["gaps"]
            }
            schema = schema_for(
                part,
                remaining_gaps=20 - len(retained_gaps),
                research_mode=self.research_mode,
            )
        request = LlmRequest(
            messages=messages,
            max_output_tokens=min(self.profile.max_output_tokens, MAX_OUTPUT_TOKENS),
            temperature=self.profile.temperature,
            reasoning_effort=self.profile.reasoning_effort,
            provider=self.profile.provider,
            profile_id=self.profile.id,
            json_schema=schema,
            schema_name=SCHEMA_NAMES[part] if part else "report_topic",
        )
        await write_state(self.checkpoints, self.digest, expected, "running")
        self.draft.attempts += 1
        started = time.perf_counter()
        try:
            result = await self.gateway.complete(
                self.profile.base_url, self.api_key, self.profile.model, request
            )
        except LlmTokenBudgetExhausted as error:
            self.account(
                error.model,
                error.prompt_tokens,
                error.completion_tokens,
                time.perf_counter() - started,
            )
            await write_state(
                self.checkpoints,
                self.digest,
                expected,
                "incomplete",
                reason="token_budget_exhausted",
            )
            raise StepExhausted from None
        except asyncio.CancelledError:
            # Root's durable gateway owns the attempt ledger and uncertain reservation.
            # Leave running intact: a resumed worker must not replay an uncertain call.
            raise
        except LlmGatewayError:
            self.account(None, None, None, time.perf_counter() - started)
            await self.pause(expected, "provider_error")
        self.account(
            result.model,
            result.prompt_tokens,
            result.completion_tokens,
            time.perf_counter() - started,
        )
        try:
            if part is not None:
                return validate_part(
                    decode(result.content),
                    part=part,
                    labels=frozenset(expected["evidence_labels"]),
                    eeis=self.eeis,
                    previous_exists=bool(self.context.previous),
                    remaining_gaps=20 - len(retained_gaps),
                    research_mode=self.research_mode,
                )
            return validate_step(
                decode(result.content),
                synthesis=topic is None,
                labels=frozenset(expected["evidence_labels"]),
                eeis=self.eeis,
            )
        except (ValueError, TypeError, RecursionError):
            # Only confirmed invalid output gets one repair. Provider failures do not.
            if topic is not None and not repair:
                return await self.call(topic, expected, repair=True)
            await self.pause(expected, "invalid_section")


async def draft_sections(
    gateway: LlmGateway,
    profile: LlmProfile,
    api_key: str,
    template: Template,
    header: ReportHeader,
    question: str | None,
    quality: QualityOfInformation,
    evidence: Sequence[EvidenceItem],
    previous: Sequence[KeyJudgement],
    direction: Direction | None = None,
    background: str | None = None,
    *,
    checkpoints: SectionCheckpoints,
    canonical_requirements: tuple[IntelligenceRequirement, ...] = (),
) -> Draft:
    """Resume unchanged validated steps; never replay an exhausted identical request.

    The gateway/job owner enforces lifetime call, token, lease and elapsed allowances.
    Native MAX deadlines recognise report_topic/report_judgements/report_context.
    """
    if not evidence:
        return no_evidence_draft(profile.model)
    context = PromptContext(
        template,
        header,
        question,
        quality,
        tuple(evidence),
        tuple(previous),
        direction,
        background,
        canonical_requirements,
    )
    try:
        topics, digest = await select_plan(context, profile, checkpoints)
        runner = _Runner(gateway, profile, api_key, context, checkpoints, digest)
    except (ValueError, TypeError, RecursionError):
        raise SectionIncomplete("planning", "invalid_packet", Draft(model=profile.model)) from None
    return await runner.run(topics)

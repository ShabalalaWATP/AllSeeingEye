"""Resume final judgement and context steps without repeating the completed topic work."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, NoReturn, Protocol

from ase.application.ports.section_checkpoints import SectionCheckpoint, SectionCheckpoints
from ase.application.reports.drafting import Draft
from ase.application.reports.sections.checkpoints import read_body, synthesis_metadata, write_state
from ase.application.reports.sections.contracts import validate_step
from ase.application.reports.sections.outcomes import SectionIncomplete, StepExhausted
from ase.application.reports.sections.synthesis_contracts import (
    CONTEXT,
    CONTEXT_PARTS,
    JUDGEMENTS,
    PARTS,
    validate_aggregate_limits,
    validate_part,
)


class SynthesisCall(Protocol):
    async def __call__(
        self,
        expected: dict[str, Any],
        *,
        part: str,
        repair: bool,
        judgements: dict[str, Any] | None,
    ) -> dict[str, Any]: ...


@dataclass(slots=True)
class _SynthesisSteps:
    checkpoints: SectionCheckpoints
    digest: str
    labels: tuple[str, ...]
    eeis: frozenset[str]
    draft: Draft
    call: SynthesisCall
    pause: Callable[[dict[str, Any], str], Awaitable[NoReturn]]
    previous_exists: bool
    research_mode: object

    def read(self, saved: SectionCheckpoint, expected: dict[str, Any]) -> dict[str, Any]:
        try:
            return read_body(
                saved,
                expected,
                self.eeis,
                previous_exists=self.previous_exists,
                research_mode=self.research_mode,
            )
        except (ValueError, TypeError, RecursionError):
            # Completed material remains immutable even when revalidation fails.
            raise SectionIncomplete(expected["id"], "invalid_checkpoint", self.draft) from None

    async def part(self, part: str, judgements: dict[str, Any] | None) -> dict[str, Any]:
        expected = synthesis_metadata(part, self.labels)
        saved = await self.checkpoints.load(self.digest, part)
        if saved and saved.status == "completed":
            return self.read(saved, expected)
        if part == CONTEXT:
            return await self.context(expected, saved, judgements)
        if saved and (
            saved.status in {"running", "split"} or saved.reason == "token_budget_exhausted"
        ):
            # Judgements and context children are leaves. Exhaustion never fans out again.
            raise SectionIncomplete(part, saved.reason or "interrupted", self.draft)
        try:
            body = await self.call(expected, part=part, repair=bool(saved), judgements=judgements)
        except StepExhausted:
            raise SectionIncomplete(part, "token_budget_exhausted", self.draft) from None
        await write_state(self.checkpoints, self.digest, expected, "completed", body=body)
        return body

    async def context(
        self,
        expected: dict[str, Any],
        saved: SectionCheckpoint | None,
        judgements: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if saved and saved.status == "running":
            raise SectionIncomplete(CONTEXT, "interrupted", self.draft)
        split = {**expected, "children": list(CONTEXT_PARTS)}
        if saved and saved.payload != (split if saved.status == "split" else expected):
            await self.pause(expected, "invalid_checkpoint")
        if not saved or saved.status != "split":
            # The old exhausted request remains in the paid-call ledger. These are
            # two new bounded identities, never a replay of report_context.
            await write_state(
                self.checkpoints, self.digest, expected, "split", children=CONTEXT_PARTS
            )
        combined: dict[str, Any] = {}
        for child in CONTEXT_PARTS:
            combined.update(await self.part(child, judgements))
        body = validate_part(
            combined,
            part=CONTEXT,
            labels=frozenset(self.labels),
            eeis=self.eeis,
            research_mode=self.research_mode,
        )
        await write_state(self.checkpoints, self.digest, expected, "completed", body=body)
        return body


async def collect_synthesis(
    checkpoints: SectionCheckpoints,
    digest: str,
    expected: dict[str, Any],
    eeis: frozenset[str],
    draft: Draft,
    *,
    call: SynthesisCall,
    pause: Callable[[dict[str, Any], str], Awaitable[NoReturn]],
    previous_exists: bool,
    research_mode: object = None,
) -> dict[str, Any]:
    steps = _SynthesisSteps(
        checkpoints,
        digest,
        tuple(expected["evidence_labels"]),
        eeis,
        draft,
        call,
        pause,
        previous_exists,
        research_mode,
    )
    saved = await checkpoints.load(digest, "synthesis")
    if saved and saved.status == "completed":
        # Existing reports and a completed new aggregate retain their original cache identity.
        return steps.read(saved, expected)
    if saved and saved.status == "running":
        # The service must explicitly resume/reset an uncertain old request first.
        raise SectionIncomplete("synthesis", "interrupted", draft)
    split = {**expected, "children": list(PARTS)}
    if saved and saved.status == "split" and saved.payload != split:
        await pause(expected, "invalid_checkpoint")
    if not saved or saved.status != "split":
        await write_state(checkpoints, digest, expected, "split", children=PARTS)
    combined: dict[str, Any] = {}
    judgements = None
    for part in PARTS:
        body = await steps.part(part, judgements)
        combined.update(body)
        if part == JUDGEMENTS:
            judgements = body
    result = validate_step(
        combined, synthesis=True, labels=frozenset(expected["evidence_labels"]), eeis=eeis
    )
    validate_aggregate_limits(result, research_mode=research_mode)
    return result

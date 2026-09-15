"""Resume final judgement and context steps without repeating the completed topic work."""

from collections.abc import Awaitable, Callable
from typing import Any, NoReturn, Protocol

from ase.application.ports.section_checkpoints import SectionCheckpoints
from ase.application.reports.drafting import Draft
from ase.application.reports.sections.checkpoints import read_body, synthesis_metadata, write_state
from ase.application.reports.sections.contracts import validate_step
from ase.application.reports.sections.outcomes import SectionIncomplete, StepExhausted
from ase.application.reports.sections.synthesis_contracts import (
    JUDGEMENTS,
    PARTS,
    validate_aggregate_limits,
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
    saved = await checkpoints.load(digest, "synthesis")
    if saved and saved.status == "completed":
        # Existing reports and a completed new aggregate retain their original cache identity.
        return read_body(saved, expected, eeis, research_mode=research_mode)
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
        child = synthesis_metadata(part, tuple(expected["evidence_labels"]))
        checkpoint = await checkpoints.load(digest, part)
        if checkpoint and checkpoint.status == "completed":
            try:
                body = read_body(
                    checkpoint,
                    child,
                    eeis,
                    previous_exists=previous_exists,
                    research_mode=research_mode,
                )
            except (ValueError, TypeError, RecursionError):
                # Do not overwrite immutable completed material that failed revalidation.
                raise SectionIncomplete(part, "invalid_checkpoint", draft) from None
        else:
            if checkpoint and (
                checkpoint.status in {"running", "split"}
                or checkpoint.reason == "token_budget_exhausted"
            ):
                raise SectionIncomplete(part, checkpoint.reason or "interrupted", draft)
            try:
                body = await call(child, part=part, repair=bool(checkpoint), judgements=judgements)
            except StepExhausted:
                raise SectionIncomplete(part, "token_budget_exhausted", draft) from None
            await write_state(checkpoints, digest, child, "completed", body=body)
        combined.update(body)
        if part == JUDGEMENTS:
            judgements = body
    result = validate_step(
        combined, synthesis=True, labels=frozenset(expected["evidence_labels"]), eeis=eeis
    )
    validate_aggregate_limits(result, research_mode=research_mode)
    return result

"""Resume historical section packets while pinning canonical brief requirements."""

from collections.abc import Sequence

from ase.application.ports.section_checkpoints import SectionCheckpoints
from ase.application.reports.sections.planning import (
    CANONICAL_METHOD_VERSION,
    LEGACY_METHOD_VERSION,
    METHOD_VERSION,
    PREVIOUS_METHOD_VERSION,
    Topic,
    packet_digest,
    plan_topics,
)
from ase.application.reports.sections.prompts import PromptContext
from ase.domain.llm import LlmProfile


async def select_plan(
    context: PromptContext,
    profile: LlmProfile,
    checkpoints: SectionCheckpoints,
) -> tuple[tuple[Topic, ...], str]:
    """A changed canonical requirement text cannot reuse an older completed section."""
    values = (
        profile,
        context.template,
        context.header,
        context.question,
        context.quality,
        context.evidence,
        context.previous,
        context.direction,
        context.background,
    )
    requirements = context.requirements
    topics = plan_topics(
        context.evidence,
        context.direction,
        requirements=requirements,
        method_version=CANONICAL_METHOD_VERSION if requirements else METHOD_VERSION,
    )
    digest = packet_digest(*values, requirements=requirements)
    if requirements or await _has_checkpoint(checkpoints, digest, topics):
        return topics, digest
    for method_version in (PREVIOUS_METHOD_VERSION, LEGACY_METHOD_VERSION):
        legacy_topics = plan_topics(
            context.evidence,
            context.direction,
            method_version=method_version,
        )
        legacy_digest = packet_digest(*values, method_version=method_version)
        if await _has_checkpoint(checkpoints, legacy_digest, legacy_topics):
            return legacy_topics, legacy_digest
    return topics, digest


async def _has_checkpoint(
    checkpoints: SectionCheckpoints,
    digest: str,
    topics: Sequence[Topic],
) -> bool:
    for section_id in ("synthesis", *(topic.id for topic in topics)):
        if await checkpoints.load(digest, section_id) is not None:
            return True
    return False

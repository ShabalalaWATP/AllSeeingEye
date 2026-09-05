"""Product templates (docs/03 section 8): what each report asks the model to write.

Rows, not code: each template names its sections and guidance, how evidence is chosen
for it, its token budget and the pipeline role it needs.
"""

from __future__ import annotations

from dataclasses import dataclass

from ase.domain.events import Category
from ase.domain.llm import LlmRole


@dataclass(frozen=True, slots=True)
class EvidenceStrategy:
    categories: frozenset[Category]  # empty means every category
    window_hours: int
    max_items: int
    per_source_cap: int


@dataclass(frozen=True, slots=True)
class Template:
    id: str
    title: str
    purpose: str
    sections: tuple[str, ...]
    strategy: EvidenceStrategy
    token_budget: int
    role: LlmRole = LlmRole.ASSESSMENT
    needs_question: bool = False
    needs_country: bool = False


ALL = frozenset[Category]()

TEMPLATES: dict[str, Template] = {
    "intsum": Template(
        id="intsum",
        title="Intelligence summary",
        purpose="A periodic summary of what happened in the scope and what it means.",
        sections=(
            "Key judgements: three to five, each a single sentence opening 'We assess' or "
            "'We judge', with exactly one yardstick term, a confidence rating and a confidence "
            "statement covering the information base, analytical rigour and volatility.",
            "Reporting by theme: what the evidence says, grouped by theme, with no yardstick "
            "terms; every item cites the evidence labels it rests on and carries their grade.",
            "Assessment: the reasoning that connects the reporting to the judgements, citing "
            "evidence.",
            "Indicators and warning: the watch condition and what changed in the period.",
            "Gaps and collection recommendations: what is not known and what would help.",
            "Sourcing statement: how many independent organisations, how much instrument data, "
            "and where syndication was counted once.",
        ),
        strategy=EvidenceStrategy(ALL, window_hours=48, max_items=40, per_source_cap=8),
        token_budget=6_000,
    ),
    "intrep": Template(
        id="intrep",
        title="Intelligence report",
        purpose="One significant event: what happened, what it means so far, what is unknown.",
        sections=(
            "Reporting: what happened, from the evidence only, with grades and citations.",
            "Key judgements: one to three initial judgements about impact or trajectory, each "
            "with one yardstick term and a confidence rating.",
            "Gaps: what is not yet known; next-update criteria as indicators.",
            "Sourcing statement.",
        ),
        strategy=EvidenceStrategy(ALL, window_hours=24, max_items=25, per_source_cap=6),
        token_budget=4_000,
    ),
    "country_brief": Template(
        id="country_brief",
        title="Country brief",
        purpose="The current picture for one nation: situation, trajectories, indicators.",
        sections=(
            "Reporting: the current situation by theme (security, political, humanitarian, "
            "hazards), from the evidence only.",
            "Key judgements: assessed trajectories, each with one yardstick term and a "
            "confidence rating.",
            "Indicators and warning: watch condition and indicators to watch.",
            "Gaps and collection recommendations.",
            "Sourcing statement.",
        ),
        strategy=EvidenceStrategy(ALL, window_hours=72, max_items=40, per_source_cap=8),
        token_budget=6_000,
        needs_country=True,
    ),
    "ask": Template(
        id="ask",
        title="Ask the Eye",
        purpose="A free-form question answered from the live evidence, judgements first.",
        sections=(
            "Key judgements answering the question, each with one yardstick term and a "
            "confidence rating; say plainly when the evidence cannot answer it.",
            "Reporting: the evidence that bears on the question, cited.",
            "Assessment: the answer in prose, citing evidence.",
            "Assumptions, alternative hypotheses and gaps.",
            "Sourcing statement.",
        ),
        strategy=EvidenceStrategy(ALL, window_hours=72, max_items=40, per_source_cap=8),
        token_budget=6_000,
        needs_question=True,
    ),
}


def template_for(template_id: str) -> Template:
    try:
        return TEMPLATES[template_id]
    except KeyError as exc:
        msg = f"Unknown template: {template_id}"
        raise ValueError(msg) from exc

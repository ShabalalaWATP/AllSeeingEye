"""Product templates (docs/03 section 8): what each report asks the model to write.

Rows, not code: each template names its sections and guidance, how evidence is chosen
for it, its token budgets and the pipeline role it needs. Section guidance lives in
``template_sections`` so a product can demand real analysis without this registry
growing past its file limit. ``token_budget`` bounds the drafting call and
``analysis_budget`` the dedicated analysis pass; both are ceilings, never targets, and
the profile's own ``max_output_tokens`` still wins when it is smaller.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ase.application.reports.template_sections import ANALYSIS_FOCUS, SECTIONS
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
    strategy: EvidenceStrategy
    token_budget: int
    #: Filled in from ``template_sections`` once the registry is built.
    sections: tuple[str, ...] = ()
    #: Output ceiling for the dedicated analysis pass, which writes the implications.
    analysis_budget: int = 0
    #: Extra analytical questions that pass must answer for this product.
    analysis_focus: tuple[str, ...] = ()
    role: LlmRole = LlmRole.ASSESSMENT
    needs_question: bool = False
    needs_country: bool = False
    needs_conflict: bool = False
    needs_hazard: bool = False


ALL = frozenset[Category]()

TEMPLATES: dict[str, Template] = {
    "intsum": Template(
        id="intsum",
        title="Intelligence summary",
        purpose="A periodic summary of what happened in the scope and what it means.",
        strategy=EvidenceStrategy(ALL, window_hours=48, max_items=40, per_source_cap=8),
        token_budget=16_000,
        analysis_budget=6_000,
    ),
    "intrep": Template(
        id="intrep",
        title="Intelligence report",
        purpose="One significant event: what happened, what it means so far, what is unknown.",
        strategy=EvidenceStrategy(ALL, window_hours=24, max_items=25, per_source_cap=6),
        token_budget=10_000,
        analysis_budget=4_000,
    ),
    "country_brief": Template(
        id="country_brief",
        title="Country brief",
        purpose="The current picture for one nation: situation, trajectories, indicators.",
        strategy=EvidenceStrategy(ALL, window_hours=72, max_items=40, per_source_cap=8),
        token_budget=16_000,
        analysis_budget=6_000,
        needs_country=True,
    ),
    "ask": Template(
        id="ask",
        title="Ask the Eye",
        purpose="A free-form question answered from the live evidence, judgements first.",
        strategy=EvidenceStrategy(ALL, window_hours=72, max_items=40, per_source_cap=8),
        token_budget=14_000,
        analysis_budget=5_000,
        needs_question=True,
    ),
    "area_brief": Template(
        id="area_brief",
        title="Area brief",
        purpose=(
            "One drawn area or map object: what is reported inside it, where that activity "
            "sits within the area, what changed during the period and what to watch there."
        ),
        strategy=EvidenceStrategy(ALL, window_hours=72, max_items=40, per_source_cap=8),
        token_budget=16_000,
        analysis_budget=6_000,
        needs_question=True,
    ),
    "disaster_sitrep": Template(
        id="disaster_sitrep",
        title="Disaster SITREP",
        purpose=(
            "One hazard's current picture: what the instruments and agencies report, who is "
            "affected, and what the response is."
        ),
        strategy=EvidenceStrategy(
            frozenset({Category.DISASTER, Category.HUMANITARIAN}),
            window_hours=72,
            max_items=40,
            per_source_cap=10,
        ),
        token_budget=12_000,
        analysis_budget=4_500,
        needs_hazard=True,
    ),
    "conflict_assessment": Template(
        id="conflict_assessment",
        title="Conflict assessment",
        purpose=(
            "One curated conflict: recent activity, assessed courses of action, warning "
            "indicators and the humanitarian picture."
        ),
        strategy=EvidenceStrategy(ALL, window_hours=168, max_items=50, per_source_cap=8),
        token_budget=20_000,
        analysis_budget=7_000,
        needs_conflict=True,
    ),
    "aviation_activity": Template(
        id="aviation_activity",
        title="Aviation activity report",
        purpose=(
            "Military and unusual flying now against the baseline, emergencies and GNSS "
            "interference, from the tracked aircraft and the day's reporting."
        ),
        strategy=EvidenceStrategy(
            frozenset({Category.AVIATION, Category.NEWS, Category.CONFLICT}),
            window_hours=24,
            max_items=50,
            per_source_cap=20,
        ),
        token_budget=12_000,
        analysis_budget=4_500,
    ),
    "maritime_activity": Template(
        id="maritime_activity",
        title="Maritime activity report",
        purpose=(
            "Broadcast warnings, exercises and closures, security incidents and GNSS notices "
            "at sea, with the shipping reporting of the period."
        ),
        strategy=EvidenceStrategy(
            frozenset({Category.MARITIME, Category.NEWS, Category.CONFLICT}),
            window_hours=72,
            max_items=50,
            per_source_cap=30,
        ),
        token_budget=12_000,
        analysis_budget=4_500,
    ),
    "cyber_summary": Template(
        id="cyber_summary",
        title="Cyber summary",
        purpose=(
            "Newly exploited vulnerabilities, ransomware claims by country and group, and "
            "internet outages and shutdowns, from the week's feeds."
        ),
        strategy=EvidenceStrategy(
            frozenset({Category.CYBER, Category.NEWS}),
            window_hours=168,
            max_items=50,
            per_source_cap=25,
        ),
        token_budget=12_000,
        analysis_budget=4_500,
    ),
}


TEMPLATES = {
    key: replace(row, sections=SECTIONS[key], analysis_focus=ANALYSIS_FOCUS[key])
    for key, row in TEMPLATES.items()
}
#: The products a drawn area or a saved map object may be written as.
AREA_TEMPLATES = frozenset({"ask", "area_brief"})
#: What a drawn-area request asking for the free-text product is promoted to.
AREA_DEFAULT_TEMPLATE = "area_brief"


def template_for(template_id: str) -> Template:
    try:
        return TEMPLATES[template_id]
    except KeyError as exc:
        msg = f"Unknown template: {template_id}"
        raise ValueError(msg) from exc

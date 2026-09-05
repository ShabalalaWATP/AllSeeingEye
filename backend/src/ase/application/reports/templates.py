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
    needs_conflict: bool = False
    needs_hazard: bool = False


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
    "disaster_sitrep": Template(
        id="disaster_sitrep",
        title="Disaster SITREP",
        purpose=(
            "One hazard's current picture: what the instruments and agencies report, who is "
            "affected, and what the response is."
        ),
        sections=(
            "Event facts: what the instrument and agency feeds report (magnitude, category, "
            "alert level, location, timing), as reporting with grades and citations.",
            "Impact and exposure: populations and places affected as reported (exposure "
            "estimates, warnings issued), cited.",
            "Response: appeals, agency actions and outbreak notices in the window, cited.",
            "Key judgements: one to three on trajectory and needs, each with one yardstick "
            "term and a confidence rating.",
            "Gaps: what is not yet known; next-update criteria as indicators.",
            "Sourcing statement.",
        ),
        strategy=EvidenceStrategy(
            frozenset({Category.DISASTER, Category.HUMANITARIAN}),
            window_hours=72,
            max_items=40,
            per_source_cap=10,
        ),
        token_budget=5_000,
        needs_hazard=True,
    ),
    "conflict_assessment": Template(
        id="conflict_assessment",
        title="Conflict assessment",
        purpose=(
            "One curated conflict: recent activity, assessed courses of action, warning "
            "indicators and the humanitarian picture."
        ),
        sections=(
            "Belligerents and objectives: who is fighting and what each side is trying to "
            "achieve, from the evidence and the curated background.",
            "Recent activity by front or theme: reporting with grades and citations, with "
            "counts where the evidence gives them.",
            "Assessed courses of action: the most likely and the most dangerous course over "
            "the next two weeks as key judgements, each with one yardstick term and a "
            "confidence rating.",
            "Indicators and warning: the watch condition and the indicators that would "
            "confirm or overturn the assessed courses.",
            "Humanitarian picture: displacement, access and outbreaks as reported, cited.",
            "Gaps and collection recommendations.",
            "Sourcing statement.",
        ),
        strategy=EvidenceStrategy(ALL, window_hours=168, max_items=50, per_source_cap=8),
        token_budget=7_000,
        needs_conflict=True,
    ),
    "aviation_activity": Template(
        id="aviation_activity",
        title="Aviation activity report",
        purpose=(
            "Military and unusual flying now against the baseline, emergencies and GNSS "
            "interference, from the tracked aircraft and the day's reporting."
        ),
        sections=(
            "Notable military and interesting flights by region: what is airborne now, from "
            "the aircraft evidence, cited by label.",
            "Patterns against baseline: which nations and watched areas are above or below "
            "their normal level, using the background figures as context.",
            "GNSS interference: where positions are degraded and what that implies.",
            "Emergencies: any emergency squawks and what is known about them.",
            "Key judgements: one to three on what the activity indicates, each with one "
            "yardstick term and a confidence rating.",
            "Gaps and sourcing statement.",
        ),
        strategy=EvidenceStrategy(
            frozenset({Category.AVIATION, Category.NEWS, Category.CONFLICT}),
            window_hours=24,
            max_items=50,
            per_source_cap=20,
        ),
        token_budget=5_000,
    ),
    "maritime_activity": Template(
        id="maritime_activity",
        title="Maritime activity report",
        purpose=(
            "Broadcast warnings, exercises and closures, security incidents and GNSS notices "
            "at sea, with the shipping reporting of the period."
        ),
        sections=(
            "Warnings by region: what the NAVAREA warnings say, by area, as reporting with "
            "grades and citations.",
            "Exercises and closures: live firing, missile and rocket areas, and where they are.",
            "Security incidents: piracy, armed robbery, attacks and suspicious approaches.",
            "GNSS interference notices and what they imply for navigation.",
            "Key judgements: one to three on the maritime picture, each with one yardstick term "
            "and a confidence rating.",
            "Gaps and sourcing statement.",
        ),
        strategy=EvidenceStrategy(
            frozenset({Category.MARITIME, Category.NEWS, Category.CONFLICT}),
            window_hours=72,
            max_items=50,
            per_source_cap=30,
        ),
        token_budget=5_000,
    ),
    "cyber_summary": Template(
        id="cyber_summary",
        title="Cyber summary",
        purpose=(
            "Newly exploited vulnerabilities, ransomware claims by country and group, and "
            "internet outages and shutdowns, from the week's feeds."
        ),
        sections=(
            "New known exploited vulnerabilities: what was added and who is affected, cited.",
            "Ransomware activity: claims by group and by nation, as reporting; remember the "
            "claims are criminal statements graded possibly true.",
            "Outages and shutdowns: where connectivity dropped and what else was happening "
            "there, cited.",
            "Key judgements: one to three on the cyber picture, each with one yardstick term "
            "and a confidence rating.",
            "Gaps and sourcing statement.",
        ),
        strategy=EvidenceStrategy(
            frozenset({Category.CYBER, Category.NEWS}),
            window_hours=168,
            max_items=50,
            per_source_cap=25,
        ),
        token_budget=5_000,
    ),
}


def template_for(template_id: str) -> Template:
    try:
        return TEMPLATES[template_id]
    except KeyError as exc:
        msg = f"Unknown template: {template_id}"
        raise ValueError(msg) from exc

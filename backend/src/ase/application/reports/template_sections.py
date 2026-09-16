"""Per-product section guidance: what an intelligence customer is owed, not a summary.

Every product keeps the same doctrine: PHIA yardstick terms with a confidence statement
in judgements, Admiralty grades and evidence labels in reporting, no yardstick terms in
reporting, nothing beyond the frozen evidence and no invented figures. What changes here
is the demand: each section must say what happened, what it means, why it matters, what
is driving it, what would have to be true for the judgement to be wrong, and what to
watch next.
"""

from __future__ import annotations

KEY_JUDGEMENTS = (
    "Key judgements: three to five, each a single sentence opening 'We assess' or "
    "'We judge', with exactly one yardstick term, a confidence rating and a confidence "
    "statement covering the information base, analytical rigour and volatility. Under each "
    "judgement give the two or three specific things that would have to be true for it to "
    "be wrong, and the indicator that would show it becoming wrong."
)
REPORTING_BY_THEME = (
    "Reporting by theme: what the evidence says, grouped by theme, with no yardstick "
    "terms; every item cites the evidence labels it rests on and carries their grade. "
    "Within each theme put the strongest and most specific reporting first, say where "
    "accounts agree, where they differ and where a single organisation is the only "
    "source, and give the reported figures exactly as reported. Do not interpret here."
)
SOURCING = (
    "Sourcing statement: how many independent organisations, how much instrument data, "
    "and where syndication was counted once. Name the sourcing weakness that most "
    "constrains the assessment."
)
GAPS = (
    "Gaps and collection recommendations: what is not known, why that matters for the "
    "judgements above, and the specific collection that would close each gap. Distinguish "
    "a gap in the evidence from a gap in the reporting. Never treat missing reporting as "
    "evidence that nothing happened."
)
INDICATORS = (
    "Indicators and warning: the watch condition and what changed in the period. Give "
    "observable, dated, falsifiable indicators, each tied to the judgement it would "
    "confirm or overturn, and say which would arrive first."
)

ANALYSIS_CORE = (
    "what it means, why it matters to the reader now, what is driving it, the second-order "
    "effects that follow if it continues, the comparison with the previous period or the "
    "stated baseline where the evidence supports one, at least one plausible alternative "
    "explanation for the same reporting, and what would have to be true for the judgement "
    "to be wrong"
)

SECTIONS: dict[str, tuple[str, ...]] = {
    "intsum": (
        KEY_JUDGEMENTS,
        REPORTING_BY_THEME,
        "Assessment: the reasoning that connects the reporting to the judgements, in "
        f"continuous prose, citing evidence. Cover {ANALYSIS_CORE}. Write several "
        "paragraphs, one analytical line of argument each, not a restatement of the "
        "reporting. Mark this clearly as assessment, distinct from what was reported.",
        INDICATORS,
        GAPS,
        SOURCING,
    ),
    "intrep": (
        "Reporting: what happened, from the evidence only, with grades and citations, "
        "including the sequence of events as reported and the points on which accounts "
        "differ. No yardstick terms.",
        "Assessment: what this event means, why it matters, what is driving it and what "
        "plausibly follows, in prose, citing evidence. Give at least one alternative "
        "explanation of the same reporting and say what would distinguish them.",
        "Key judgements: one to three initial judgements about impact or trajectory, each "
        "with one yardstick term and a confidence rating, each naming what would have to "
        "be true for it to be wrong.",
        "Gaps: what is not yet known, why it matters, and next-update criteria as "
        "specific indicators.",
        SOURCING,
    ),
    "country_brief": (
        "Reporting: the current situation by theme (security, political, humanitarian, "
        "hazards), from the evidence only, with grades and citations and no yardstick "
        "terms. Say where accounts differ and where one organisation is the only source.",
        "Assessment: how the themes interact, what is driving the current trajectory, "
        f"what follows if it continues, and {ANALYSIS_CORE}. Compare with the previous "
        "period where the evidence supports it. Prose, citing evidence, clearly marked "
        "as assessment.",
        "Key judgements: assessed trajectories, each with one yardstick term, a confidence "
        "rating and the conditions that would falsify it.",
        INDICATORS,
        GAPS,
        SOURCING,
    ),
    "area_brief": (
        "Reporting by theme within the area: what the evidence says about this drawn area "
        "and the period, grouped by theme, with grades and citations and no yardstick "
        "terms. A drawn area is a collection choice: an item being in the pool is not "
        "evidence that it happened inside the box, and a publisher's remit is not "
        "geography. State for each item what located it, and say plainly when location is "
        "asserted by the publisher rather than established.",
        "Distribution within the area: where activity is concentrated inside the area and "
        "where it is absent, using only locations the evidence states. Say where the "
        "absence is a collection gap rather than quiet ground.",
        "Change during the period: what changed inside the area during the period against "
        "the earliest reporting in the pool, and what did not. Do not assert a trend the "
        "evidence cannot carry.",
        "Assessment: the answer to the question asked of this area, in prose, citing "
        f"evidence. Cover {ANALYSIS_CORE}. Say what the area's boundary includes and "
        "excludes that changes the answer. Clearly marked as assessment.",
        "Key judgements about the area, each a single sentence with one yardstick term, a "
        "confidence rating and a confidence statement; say plainly when the evidence "
        "cannot answer the question for this area.",
        "Assumptions and alternative hypotheses, including the alternative that the "
        "pattern is an artefact of which sources cover this area.",
        "Indicators and warning for this area: observable, dated indicators inside or "
        "adjacent to the area that would confirm or overturn the judgements.",
        GAPS,
        SOURCING,
    ),
    "ask": (
        "Key judgements answering the question, each with one yardstick term and a "
        "confidence rating; say plainly when the evidence cannot answer it, and name the "
        "conditions that would falsify each judgement.",
        "Reporting: the evidence that bears on the question, cited, with grades and no "
        "yardstick terms.",
        "Assessment: the answer in prose, citing evidence, covering "
        f"{ANALYSIS_CORE}. Explain the reasoning rather than repeating the reporting.",
        "Assumptions, alternative hypotheses and gaps: name the lynchpin assumptions, give "
        "at least one competing explanation and what would distinguish it, and say what "
        "collection would resolve the question.",
        SOURCING,
    ),
    "disaster_sitrep": (
        "Event facts: what the instrument and agency feeds report (magnitude, category, "
        "alert level, location, timing), as reporting with grades and citations. Report "
        "figures exactly as given and never convert or estimate them.",
        "Impact and exposure: populations and places affected as reported (exposure "
        "estimates, warnings issued), cited, with the reporting basis of each estimate.",
        "Response: appeals, agency actions and outbreak notices in the window, cited.",
        "Assessment: what the reported facts imply for the next days, what is driving the "
        "trajectory, the second-order effects on access, health and displacement, and the "
        "comparison with the earlier reporting in this window. Prose, citing evidence, "
        "clearly marked as assessment.",
        "Key judgements: one to three on trajectory and needs, each with one yardstick "
        "term, a confidence rating and its falsifying condition.",
        "Gaps: what is not yet known, why it matters, and next-update criteria as indicators.",
        SOURCING,
    ),
    "conflict_assessment": (
        "Belligerents and objectives: who is fighting and what each side is trying to "
        "achieve, from the evidence and the curated background.",
        "Recent activity by front or theme: reporting with grades and citations, with "
        "counts where the evidence gives them and no yardstick terms.",
        "Assessment: how the activity relates to each side's objectives, what is driving "
        f"the current pattern, and {ANALYSIS_CORE}. Compare with the earlier part of the "
        "period where the evidence supports it. Prose, clearly marked as assessment.",
        "Assessed courses of action: the most likely and the most dangerous course over "
        "the next two weeks as key judgements, each with one yardstick term, a confidence "
        "rating and the conditions that would falsify it.",
        "Indicators and warning: the watch condition and the observable indicators that "
        "would confirm or overturn the assessed courses, ordered by which would arrive "
        "first.",
        "Humanitarian picture: displacement, access and outbreaks as reported, cited, and "
        "what the military picture implies for it.",
        GAPS,
        SOURCING,
    ),
    "aviation_activity": (
        "Notable military and interesting flights by region: what is airborne now, from "
        "the aircraft evidence, cited by label and with no yardstick terms.",
        "Patterns against baseline: which nations and watched areas are above or below "
        "their normal level, using the background figures as context. Give the comparison "
        "explicitly and say when the baseline is unknown rather than implying one.",
        "GNSS interference: where positions are degraded and what that implies. Degraded "
        "positions are not proof of jamming or of attribution.",
        "Emergencies: any emergency squawks and what is known about them.",
        "Assessment: what the activity and the departures from baseline indicate, what is "
        "driving them, what follows if the pattern holds, and at least one alternative "
        "explanation, including routine training and coverage artefacts. Prose, citing "
        "evidence, clearly marked as assessment.",
        "Key judgements: one to three on what the activity indicates, each with one "
        "yardstick term, a confidence rating and its falsifying condition.",
        "Gaps and sourcing statement, naming the coverage limits of the tracking data.",
    ),
    "maritime_activity": (
        "Warnings by region: what the NAVAREA warnings say, by area, as reporting with "
        "grades and citations and no yardstick terms.",
        "Exercises and closures: live firing, missile and rocket areas, and where they are.",
        "Security incidents: piracy, armed robbery, attacks and suspicious approaches.",
        "GNSS interference notices and what they imply for navigation.",
        "Assessment: what the warnings, closures and incidents together indicate for "
        "shipping in the period, what is driving them, the second-order effects on routing "
        "and insurance where the evidence supports it, and at least one alternative "
        "explanation. Prose, citing evidence, clearly marked as assessment.",
        "Key judgements: one to three on the maritime picture, each with one yardstick "
        "term, a confidence rating and its falsifying condition.",
        "Gaps and sourcing statement, naming what under-reporting at sea conceals.",
    ),
    "cyber_summary": (
        "New known exploited vulnerabilities: what was added and who is affected, cited, "
        "with no yardstick terms.",
        "Ransomware activity: claims by group and by nation, as reporting; remember the "
        "claims are criminal statements graded possibly true and are not confirmed "
        "compromises.",
        "Outages and shutdowns: where connectivity dropped and what else was happening "
        "there, cited. Correlation in time is not attribution.",
        "Assessment: what the week's additions, claims and outages mean for exposure, who "
        "is driving them, the second-order effects, the comparison with the earlier part "
        "of the window where the evidence supports it, and at least one alternative "
        "explanation for any apparent campaign. Prose, cited, clearly marked as "
        "assessment.",
        "Key judgements: one to three on the cyber picture, each with one yardstick term, "
        "a confidence rating and its falsifying condition.",
        "Gaps and sourcing statement, naming the reporting bias in criminal leak sites.",
    ),
}

#: Extra analytical questions the dedicated analysis pass must answer for a product.
#: These are demands on reasoning, never licence to go beyond the frozen evidence.
ANALYSIS_FOCUS: dict[str, tuple[str, ...]] = {
    "intsum": (
        "Which single development in this period most changes the picture, and why.",
        "What connects the themes: a common driver, or unrelated coincidence.",
        "What the period looks like against the previous one, where the evidence allows.",
    ),
    "intrep": (
        "Why this event happened now, on the evidence available.",
        "What follows in the next days if nothing intervenes.",
    ),
    "country_brief": (
        "Which trajectory is most consequential for the country and why.",
        "Where the security, political and humanitarian pictures reinforce each other.",
    ),
    "area_brief": (
        "What the geography of the reporting inside the area does and does not establish.",
        "Whether the pattern inside the area is real or an artefact of source coverage.",
        "What the area's boundary excludes that would change the answer.",
    ),
    "ask": (
        "The strongest competing answer to the question and what would distinguish it.",
        "What the evidence cannot settle, and why that limits the answer.",
    ),
    "disaster_sitrep": (
        "What the reported exposure implies for need over the coming days.",
        "Which response gap is most consequential on the evidence.",
    ),
    "conflict_assessment": (
        "How recent activity serves or frustrates each side's stated objectives.",
        "Which indicator would most cheaply separate the likely from the dangerous course.",
    ),
    "aviation_activity": (
        "Whether the departure from baseline is activity or coverage.",
        "What the pattern of airframes and areas suggests about intent, if anything.",
    ),
    "maritime_activity": (
        "What the warnings and incidents together imply for routing decisions.",
        "Where under-reporting most distorts the picture.",
    ),
    "cyber_summary": (
        "Whether the week's claims indicate a campaign or independent opportunism.",
        "Which newly exploited vulnerability has the widest exposure on this evidence.",
    ),
}

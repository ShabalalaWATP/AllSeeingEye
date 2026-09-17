# Report quality checks

What runs over a drafted report before it is frozen, what each check catches, and what
none of them can catch. Every check produces findings. A finding never rewrites the
report: an error-severity finding from one of these rules becomes a visible reason on
the report's status, and the report becomes `needs_review`.

The rule names are defined once in `backend/src/ase/domain/report_quality_rules.py`
and are what you see in the `rule` field of a report's findings.

| Order | Rule | Cost | What it catches |
| --- | --- | --- | --- |
| 1 | `figure_consistency`, `date_consistency` | free | A figure or date in the prose the frozen evidence does not carry |
| 2 | `template_structure`, `house_style` | free | A missing or misordered section, a count or length outside the template, American spelling, dashes, stray markup, inline citations |
| 3 | `source_sufficiency` | free | A source mix the template expects and the citations do not have |
| 4 | `requirement_gate` | free | A PIR, SIR or EEI that is neither answered nor disclosed as a gap |
| 5 | `contradiction` | free | Which sources disagree with a judgement, with their grades and character |
| 6 | `entailment` | one model call | A citation that is present and correctly quoted but does not support the claim |

The existing `requirement_coverage` rule (raised by the section pipeline) and the
doctrine, citation and assessment checks are unchanged and still gate the report.

## 1. Figures and dates

`ase/domain/report_figures.py` parses counts, percentages, percentage points, currency
amounts and calendar dates out of the prose, then out of the frozen evidence's titles,
summaries, attributes and dates. A prose figure passes when the evidence states it,
when the evidence value rounds to it, or when the checker can reproduce it as a sum or
difference of stated figures.

- A figure written to a round place carries half that place, capped at a tenth of the
  figure; an approximated figure also carries two per cent. So "about 3,000" accepts a
  stated 2,987 and reports a stated 2,500, which is a fifth of the way off.
- A percentage and a percentage point are different kinds and never match each other.
  A currency amount must match its currency.
- A range is checked at both ends.
- Durations ("over the next two weeks", "in the last 14 days"), bare small integers
  ("three fronts"), evidence labels, requirement identifiers and Admiralty grades are
  not figures.
- The confidence and sourcing statements are not checked: the engine writes item
  counts and an instrument share into them, so their figures describe the evidence
  base rather than a claim about the world.
- A date passes when a frozen source carries it or when it falls inside the reporting
  period. A date outside the period with no source is reported.

## 2. Structure and house style

`ase/domain/report_structure.py` holds one row per template: the parts of the body it
requires, the section headings it asks for and their order, how many key judgements it
expects, and the length bounds of the finished prose. `ase/domain/house_style.py`
holds the spelling pairs and the punctuation and markup rules.

Style problems are reported, never corrected. Correcting a model's words silently
would change what the report says with no record that it happened.

## 3. Source mix

`ase/domain/source_character.py` assigns a character to each feed identifier, for
example a national CERT, a security vendor, an independent outlet, a state-aligned
outlet or instrument data. An unlisted feed falls back to its declared provenance role
and is otherwise left unclassified rather than guessed at.

`ase/domain/source_requirements.py` says what mix each template expects, counting
distinct organisations among the sources the report actually cites:

| Template | Expects | Minimum organisations |
| --- | --- | --- |
| `intsum` | no particular mix | 3 |
| `intrep` | no particular mix | 2 |
| `country_brief` | an official issuer, an independent outlet | 2 |
| `ask` | no particular mix | 2 |
| `disaster_sitrep` | instrument data or an official issuer, a humanitarian agency | 2 |
| `conflict_assessment` | an independent outlet or a research body | 3 |
| `aviation_activity` | instrument data | 1 |
| `maritime_activity` | an official issuer | 1 |
| `cyber_summary` | a vendor advisory, a national CERT | 2 |

An unmet expectation is stated on the report. When the report's own sourcing statement
or gaps already disclose the gap, the note drops to advisory, so a report that admits
what it lacks is not punished for saying so. A report whose citations all come from one
organisation always says so.

To change what a template expects, edit its row. The requirements are data, not
conditionals spread through the pipeline.

## 4. Requirement coverage

The section pipeline already adds a neutral gap notice for an unanswered EEI. Nothing
looked at the PIR or the SIRs. `requirement_gate` counts a requirement as covered when
a section names it and cites evidence, when the prose answers its question, or when the
report lists it as a gap. Anything left is named with its question.

## 5. Contradiction

Where a judgement cites counterevidence, the report carries one sentence naming both
sides with their source names, grades and character, and saying which side is stronger.
Equal or stronger opposition remains a review reason; weaker opposition is advisory.

## 6. Entailment

One bounded model call, metered through the AI allowance ledger like every other call
in the pipeline, recorded with the purpose `report:<template>:entailment`.

- It reads only the key judgements (at most 5) and at most 3 cited extracts each, each
  extract cut to 400 characters.
- It answers with a fixed schema: `supports`, `partly_supports` or `does_not_support`,
  with a short reason. A verdict on a pair that was never asked about is dropped.
- Expected cost is roughly 2,000 to 2,500 prompt tokens and up to 1,200 completion
  tokens, so about 3,000 to 3,700 tokens per report. The allowance reservation is the
  completion budget plus the measured prompt size.
- `does_not_support` is a review reason. `partly_supports` is advisory.
- With no assessment-role profile, no allowance, or a failed or unusable answer, the
  report says the check did not run and stays exactly as drafted.

## What none of this can check

- Whether a judgement is true. Every check above is about wording, arithmetic,
  structure and provenance metadata.
- Whether a source is right. Grades are inherited editorial policy, not measured
  accuracy, and the source character table is a collection fact.
- Whether two sources are genuinely independent. Declared organisation grouping is a
  declaration, not a verified chain.
- Figures a source states only inside a full article the engine never retained: the
  checks see titles, summaries, attributes and dates.
- Units on counts. "3,000 people" and "3,000 vehicles" are not distinguished, because
  unit words in prose are too unreliable to gate on. Percentages, percentage points and
  currencies are distinguished.
- Whether a correction an analyst makes is right. Nothing here edits the report.

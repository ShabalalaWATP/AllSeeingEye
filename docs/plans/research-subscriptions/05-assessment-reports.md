# Packet 5: stronger assessment and one professional product

Goal: improve what can be substantiated, preserve meaningful uncertainty and carry the same findings into the reader, Word, PDF and Markdown. Extend the existing evidence matrix, claim ledger and canonical document pipeline.

## A01: source grades, original claims and review history

Dependencies: E02, E03. Ownership: `domain/source_ratings.py`, `domain/source_provenance.py`, `domain/evidence_matrix.py`, grading adapters and policy history.

Implementation:

1. Separate issuer authenticity (this institution published this text) from credibility of the underlying assertion. Keep A–F source reliability and 1–6 information credibility as qualitative assessments, not percentages or a multiplied truth score.
2. Record rating scope/subject expertise, basis, assessor type, reviewed date, policy version and review history. Unknown source competence remains unknown; a source's political origin alone does not assign truth or falsehood.
3. Harmonise initial feed, fresh research, retained map context and later regrading through one explicit policy adapter. Where historical policies differ, freeze the applied policy and add a review note, not an unannounced regrade of old reports.
4. Extend origin relationships: original document/statement, direct witness, republication, translation, citation chain and possible shared anonymous origin. Each edge has a reason and provenance. Model-suggested relationships are proposals until supported by an observable link/passage or reviewed; uncertainty should reduce apparent independence, not be resolved by guessing.
5. Retain conservative confidence ceilings. One strong source can contribute more than several weak copies, but no quantity of articles becomes a mathematical probability. Preserve the existing “one strong group may support Moderate; High needs suitable independent strong support without material concerns” policy unless a separately evaluated policy change is documented.
6. Freeze ratings/origin groups with report evidence; current source corrections/history are visible separately. Do not let third-party rating data or an LLM arbitrarily overwrite reviewer decisions.

Tests: one strong source versus three weak tabloids, three translations of one claim, contradictory official releases, primary statistical dataset versus opinion piece, same government-issuer rule across countries, unknown anonymous origins, rating revision and unchanged historical exports.

Done when source selection/assessment uses consistent documented inputs and no UI advertises article counts as confidence or likelihood.

## A02: claim adjudication and consistent doctrine

Dependencies: A01, E05. Ownership: existing `domain/claim_ledger.py`, `domain/reports.py`, `domain/validation.py`, `domain/judgement_assessment.py`, citation checks, staged contracts and doctrine reference integration.

Extend each material claim/judgement with:

| Field | Rule |
| --- | --- |
| Stable claim ID and type | Reported observation, attributed claim, analytical judgement or forecast. Exact text and requirement IDs retained. |
| Applicability | Observation period/location/entities; forecasts additionally need horizon end, observable resolution criterion and review date. “Cannot assess” is valid. |
| Evidence relationships | Exact frozen passage IDs, support/opposition/context role, original source group, relation rationale and relevant dates. |
| Support result | Supported, partly supported, contradicted, insufficient context or not assessed. Record method/version and reviewed versus automated proposal. |
| Likelihood | Existing PHIA band for applicable analytical propositions. Do not force every historical fact or unknown future into a probability band. |
| Confidence | Existing High/Moderate/Low, constrained by evidence policy, with separate information-base, analytical-rigour and complexity/volatility explanations. “Not assessed” must be explicit where supported by the schema. |
| Assumptions and changes | Assumption IDs, material counterarguments, disconfirming indicators and links to prior claim revisions. |

Use deterministic checks for citation existence, exact passage membership, numbers/units/date/attribution consistency and required fields. Add a bounded model adjudication step that compares material claims against original passages and contrary passages; reject invented evidence IDs. Its output is an inspectable proposal, not proof of truth. Literal mismatches may require review rather than immediate factual rejection, particularly for translation or paraphrase.

Apply the same doctrine checks to direct, staged, resumed, scheduled, repaired and imported model-result paths. Preserve the seven PHIA bands/ranges in `domain/doctrine.py`; do not introduce a rival scale. Fix forbidden-vocabulary checks across paths and reject judgement assertions mixing “highly likely” with an incompatible “100% probability”. Legitimate quoted source statistics such as inflation or survey percentages remain permitted and attributed. Reported facts must not silently contain the model's unlabelled forecasts.

Require non-empty, specific rationale fields, but do not pretend word-count rules measure analytical quality. A generic “Because.” fails the structural minimum; adequacy is measured in V01. Add an alternative explanation for consequential single-judgement reports when supported, rather than only when multiple judgements happen to exist. Do not invent alternatives solely for a fixed count.

Reuse the existing public doctrine reference pack available to Ask Eye. Pin official PHIA/MOD/NATO source URLs, edition/publication dates, retrieval dates, permitted excerpts and hashes in its current registry. Validate current editions when implementation reaches this task; do not download unknown replacements or claim NATO accreditation. Put operational guidance into prompts and validation where it maps to a concrete rule, not a decorative “NATO compliant” badge.

Reference basis already used by the audit: [PHIA uncertainty guidance](https://www.gov.uk/government/publications/explaining-uncertainty-in-uk-intelligence-assessment/explaining-uncertainty-in-uk-intelligence-assessment) and [Common Analytical Standards](https://www.gov.uk/government/publications/phia-common-analytical-standards/phia-common-analytical-standards). Public NATO/MOD documents must retain their exact verified edition and scope. A probability label generated by a model is not calibrated without later resolved forecasts.

Tests: the two audited validation probes, missing horizon/resolution criterion, empty/generic rationale, legitimate numerical statistics, number/unit/negation/date mismatch, unavailable original passage, translated text, fabricated citation, conflicting support and lens invariance. Add integration cases through every active production path.

## A03: final quality gate and canonical report

Dependencies: A02. Ownership: `application/reports/production_version.py`, `document.py`, assessment projection, current renderers and reader status components.

Compute final status after requirement coverage, challenge, citation/adjudication and structural validation have completed. Keep auditable components rather than compressing quality into an unexplained numerical score.

Materiality is anchored to explicit required requirements, their priority and declared consequential claims; model suggestions cannot downgrade mandatory checks. Missing, skipped, invalid, timed-out or interrupted required adjudication yields `not_assessed` with a reason and Needs review. Absence of findings is not a pass. Human baseline acceptance preserves the original automated assessment and its missing-check reason.

| Condition | Product outcome |
| --- | --- |
| Unusable/invalid output, no authorised product, irrecoverable generation failure | Failed; no polished normal report pretending success. Retain authorised diagnostics/drafts separately. |
| Material unsupported/contradicted judgement, unresolved material citation issue or missing mandatory requirement | Needs review with concise prominent reasons. |
| Usable analysis but required source/date coverage incomplete | Partial coverage and, where it compromises a material judgement, Needs review. Keep both quality and coverage axes. |
| Structural checks complete and material adjudication/coverage criteria pass | Ready, labelled as automated checks passed, not independently verified truth. |
| No new relevant captured evidence with adequate planned coverage | Short quiet-period edition with scope and limitations, not a failed or padded long report. |

A human acceptance decision can resolve review workflow but cannot erase evidence concerns. Record who accepted what and preserve the original automated result. Legacy reports without adjudication remain legacy/not-assessed; do not relabel them fact-checked.

Canonical product order:

1. Title, observation dates, optional forecast horizon and issued date.
2. Concise review/coverage status if material; executive summary.
3. Key judgements, probability where applicable, confidence and meaningful counterevidence beside the affected assessment.
4. Sourced findings by requirement, with appropriate tables/figures/timeline.
5. Implications for the chosen lens, alternative explanations, outlook/indicators.
6. Material limitations, concise method note and reference list. Detailed source receipts/usage stay in the supporting workspace.

In-text citations and references must resolve to the exact frozen evidence, including passages for relevant claims. Project `version.challenge` and `citation_checks` into this canonical model; do not only suppress legacy advocacy and then omit its replacement. Keep model names, reasoning settings, provider debug text and token details outside normal report prose. The concise method note can identify public-doctrine-informed practice without claiming official certification.

Use current HTML/Word/PDF/Markdown exporters and sanitisation. Charts require captions, units, data/source notes and a text equivalent. Word gets proper heading styles, tables and reference links. PDF needs repeated table headers/page breaks and visible review status. Markdown uses portable links/tables plus packaged images where needed. Exports must retain the same conclusions/warnings/reference IDs as the reader, and recheck exact-version authority at release.

Tests: material challenge/citation warning visible near claim and near start in every format; no operational model data leaked; numbered references stable; unsupported chart/HTML/link injection safe; revoked access during render; older version export unchanged. V03 must render real sample documents and inspect pages, not only compare strings.

## A04: explainable changes, baselines and novelty

Dependencies: A02, S04, E04. Ownership: `domain/research_changes.py`, subscription history, comparison service and canonical change summary.

Preserve existing content fingerprints, previous-judgement context and quiet-period guidance. Extend comparison to claim meaning, likelihood band, horizon, support/opposition, assumptions, indicators and corrections, not merely evidence IDs/confidence.

Persist exact previous/current report versions and stable claim mappings. Use deterministic IDs/entity/date fields first; a bounded model can propose semantic matches and materiality with cited reasons. Ambiguous matches are unresolved, not automatically “unchanged”. Do not infer changed confidence from a publisher's reputation change alone or treat a rewritten headline as new independent evidence.

Expose six comparison states with safe precedence: failure; insufficient coverage; significant contradiction/correction; assessment changed; new evidence with broadly unchanged assessment; no new relevant captured evidence. Store multiple reasons where relevant even if one state headlines the edition.

Examples to implement:

- Same evidence IDs and confidence, but likelihood changes from unlikely to likely: assessment changed with explanation, not no change.
- Ten syndicated articles repeating the same original report: provenance/source churn, not ten new developments.
- An official source corrects a number at the same URL: correction linked to both preserved versions.
- No provider could be reached: insufficient/failed collection, not “nothing happened”.
- New facts but unchanged judgement: show the facts and why the assessment stands.
- Quiet interval with adequate coverage: short update, dates, coverage and watch conditions. Do not regurgitate full background.

Comparison baseline is the last eligible/explicitly accepted successful edition from S02, with compatible scope and version. Changing topic/AOI materially requires a fresh baseline or a clearly labelled limited comparison; do not compare unrelated editions silently. Failed attempts never erase fingerprints/cutoffs.

Tests: each example, probability-only/meaning-only change, swapped claims, amended horizon, inaccessible baseline, changed brief, repeated URLs/corrections and independent provider outage. Notify according to user policy and the S05 outbox; a model's materiality assertion without valid claims/evidence cannot trigger a definitive factual alert.

## A05: tier-scaled synthesis and requirement coverage

Dependencies: A03, A04, R04. Ownership: staged planning/synthesis contracts, continuation payload bounds and report coverage projection.

Apply R04's judgement/alternative maxima per depth, replacing the universal two-judgement limit. Treat maxima as limits, not targets. Keep initial topics grouped and bounded, enforce per-stage schemas and reduce optional scope explicitly if model/context capacity is insufficient.

Each required question maps to selected evidence, findings and a state: answered, partially answered, disputed or no adequate evidence. Missing requirements cannot vanish during synthesis. One supported finding can answer multiple related requirements without duplicate prose. The executive summary should convey implications rather than list every section.

Define a bounded stage plan before drafting: initial planning, optional query/task planning, up to six initial topic calls with bounded split leaves, two synthesis calls, challenge/adjudication calls and at most one affected redraft pass. Dispatch each only if the existing total job call/token/time allowance permits it. Reserve for final validation/synthesis first; optional specialist work cannot consume all remaining allowance. Persist completed steps and never repeat them merely to obtain longer prose.

Use the executable reservation table already introduced by R04. Do not create a second counter here. Verify all twelve Advanced requirement IDs survived the versioned Direction bridge before drafting; the coverage matrix cannot recover requirements truncated earlier.

Review the current 20-record/24 KiB continuation view against larger packets. Select representative records by requirement/origin under a deliberate byte cap and include a coverage manifest; do not blindly attach all full text. A truncated packet must be disclosed to the planning model and recorded in receipts.

Tests: maximum Advanced requirements remain represented, tiny evidence yields honest short output, failed section remains visible as a gap, oversized model answer splits/reuses safely, optional stages skipped with reason, final total call/token limits and deterministic citation numbering. V01 compares quality by tier; extra words alone do not demonstrate depth.

# Packet 3: shared briefs, lenses and meaningful depth

Goal: the same versioned research question, sources, scope and output preferences power one-off Research and Subscriptions.

## R01: canonical Research Brief

Dependencies: C01, S01. Ownership: domain/application brief contracts, persistence, API schemas and generated client contracts.

Read current `backend/src/ase/application/reports/request.py`, `domain/research_scope.py`, `domain/research_plan.py`, `domain/research_tasks.py`, `domain/research_area.py`, schedule schemas and private input authority rules.

Create small responsibility-based modules under `domain/` and `application/research/` for a versioned brief, validation and request conversion. Reuse existing value objects and limits rather than storing an unvalidated arbitrary JSON prompt.

| Group | Required contract |
| --- | --- |
| Identity | Brief ID/revision/schema version; owner/team; title; optional preset ID/version; created/revised times. Immutable published revisions. |
| Question | Main question; up to 12 stable-ID intelligence requirements, each with required/optional and priority. Required count is bounded by the chosen depth before dispatch. |
| Scope | Existing country/entity selectors, reviewed aliases, conflict/hazard selectors and optional exact AOI with geometry version/hash; plan/parent report and exact version references. |
| Time | Observation policy and explicit or relative interval; separate optional forecast horizon; timezone belongs to subscription scheduling, not evidence dates. |
| Lens | Enumerated lens ID, audience, decision need and editable relevance instructions. No preferred factual conclusion. |
| Collection | Authorised public terms and accepted variants, languages, focus/subject, selected source IDs/policy, web-search choice, admitted tasks and hypotheses, required primary/local/opposition coverage. |
| Private inputs | Existing authorised durable input references and disclosure flags. Session-expiring inputs cannot silently become permanent subscription attachments; show renewal requirements or require existing durable report evidence. |
| Output | Basic/Deep/Advanced, output language, existing style/template choice, preferred sections, accessible chart/table preferences. |
| Limits | Versioned policy ID plus user limits no higher than authorised system/model caps; maximum passes, external operations, tokens and time. |
| Monitoring | Indicators, review conditions, novelty preference and optional voluntary organisation/sector profile reference. |

Proposed new text limits: main question 2,000 characters, each requirement 500, lens/audience/decision text 1,000 each, exclusions 10 entries of 300. Preserve tighter current scope/input limits; reject rather than silently truncate. Use the stricter existing admission/checkpoint byte cap for the complete request. Return field-level errors before job creation. Store only IDs/sanitised inputs, no credentials or live raw-event dumps.

Distinguish reusable brief definition from execution snapshot. Resolve relative dates, exact private access and model assignment once at admission. The frozen run snapshot includes that resolved brief revision and effective collection plan. A preset edit must never change saved briefs or historical runs.

Canonical requirement IDs/text must survive independently of tolerant legacy Direction decoding, which currently truncates EEIs to ten and shortens text. Do not send twelve Advanced requirements through that lossy adapter. Version the bridge and test all twelve IDs/texts through planning, checkpoint/resume, synthesis, coverage and exports before exposing the twelve-question option.

Migration: add brief/revision storage and nullable schedule/job references; adapt old requests to a versioned “legacy-derived” brief. Do not insert fictional missing preferences or transform historical output. Old endpoints may accept old payloads during transition through one canonical converter. Compare old/new payloads for behavioural equivalence.

Tests: all fields round-trip, overlong/deep payload rejection, immutable revision, cross-team access, legacy default preservation, transient-input failure and no private query leakage. Done when one canonical converter drives both job and edition admission.

## R02: one brief across entry points

Dependencies: R01, C03, S02. Ownership: request conversion, frontend shared brief state/API client, report/map/schedule handoff.

Research, Run once, Save brief and Subscribe serialise the same brief revision. Subscribe adds recurrence/window/delivery/budget policies only. Keep output language/style, translated variants, hypotheses, planned tasks, source exclusions and private disclosure flags intact.

From a report, choose the exact selected version and offer “Use this brief” and “Subscribe to updates”. Copy the definition, not its old resolved clock. Let the user choose future rolling or since-last-success coverage. Preserve the historical report as optional baseline and show any incompatible scope changes. An unrelated prior report cannot become a valid baseline simply because its ID was pasted.

From the map, retain exact saved geometry/version, selected question and allowed map-source context. A map screenshot, bounding box or country centroid is not a replacement for the polygon. Existing area disclosure controls remain explicit.

Keep shared state below feature boundaries (for example `frontend/src/components/research/` plus `lib/` contracts and a brief hook). Do not move geolocation back into Research. Generated `openapi.json`/`types.gen.ts` come from the backend schema, never hand-edited types alone.

Tests: a maximal valid brief submitted through one-off and subscription produces equivalent resolved settings at the same frozen time; map polygon survives; report selected version survives; expired private evidence is actionable; editor cancel leaves saved revision unchanged.

## R03: presets and lenses

Dependencies: R02, E00. Ownership: validated backend resource catalogue/service, shared preset picker and personal saved briefs.

Implement all 20 starters in [PRESETS.md](PRESETS.md). Store machine-readable, schema-validated resources (proposed `backend/src/ase/resources/research_presets.json`) and resolve source bundles through actual source IDs from E00. E03 later implements additional bridges and live verification. Each preset needs ID/version, title, short purpose, owner role, review date, requirements, suggested languages, lens choices, sources/capability dependencies, sections and indicators. Unknown source IDs fail catalogue validation. A proposed but unimplemented capability uses a separate declared gap record, never a fake executable source ID. An unavailable key-required source remains a visible gap, not a silently omitted requirement.

Use a searchable grouped library: Conflict, Cyber, Economy, Cross-cutting, My briefs. Cards show purpose, coverage and editable starting settings. Default to Deep for curated analytic presets; allow Basic with a reduced selected requirement set and an explicit preview. A blank custom question can retain Basic as the lightweight default.

Lens options: general situational awareness, UK policy, civilian protection, regional security, economic exposure, energy security, supply-chain impact, defensive cyber and clearly labelled actor-perspective analysis. An actor perspective examines stated aims, constraints and claims; it cannot suppress counterevidence or direct the model to reach a preferred conclusion. Source grades and likelihood rules do not change with lens.

Users can save, rename, duplicate and version their own briefs. Team sharing follows existing permissions only; no new team workflow. Preset updates show a diff and require an explicit user adoption into a saved brief. Capability tests verify every required bundle has at least one supported route or a declared setup gap for the scope/language.

Tests: all starter resources validate, all topics searchable, lenses persist, no conclusion bias instruction, preset revision pinning, private/shared saved brief permissions and unavailable source disclosure.

## R04: depth, clarification and preflight

Dependencies: R02, R03. Ownership: current research preview/budget/depth policy, planning prompts and client preview.

Initial depth policy retains current collection ceilings while reallocating work. Values are ceilings, not an obligation to pad reports or always exhaust the budget.

| Depth | Required questions | Key judgements, maximum | Alternatives, maximum | Fresh source operations / collection time | Selected public evidence | Indicative words |
| --- | --- | --- | --- | --- | --- | --- |
| Basic | 1–3 | 3 | 2 | 6 / 45 seconds | 24 | 500–900 |
| Deep | 1–6 | 5 | 3 | 24 / 180 seconds | 48 | 1,200–2,000 |
| Advanced | 1–12 | 8 | 4 | 32 / 240 seconds | 80 | 2,500–4,000 |

Basic answers the central requirement, main limitations and short outlook. Deep adds primary passages, timeline and contrary evidence. Advanced adds multiple explicit hypotheses, selected typed quantitative work, indicators and an evidence appendix. No evidence means abstention/shorter output, not fabrication to satisfy a word target. Required questions beyond the tier limit must be reduced by the user or a higher tier selected, never silently dropped.

These source budgets are separate from the existing durable job's model-call/token/deadline caps. Initial task topics may remain at six and group related requirements; A05 scales synthesis carefully and retains bounded splitting. Optional agent work shares the same caps; do not multiply 24 LLM calls by each stage or each subscription retry.

Implement the executable stage-reservation contract here, before E05 or A02 adds new work. The following is an initial maximum dispatch allocation within the existing 24-call ceiling, not a promise every task is performed:

| Model work | Maximum dispatches |
| --- | ---: |
| Direction/brief planning | 1 |
| Optional supplementary task planning | 1 |
| Optional query translation | 1 |
| Optional legacy initial continuation | 1 |
| Initial topic drafting including failed parent calls and splits | 8 |
| Initial synthesis | 2 |
| Post-draft challenge query planning | 1 |
| Post-draft challenge review | 1 |
| Affected topic redrafts | 2 |
| Updated synthesis, when required | 2 |
| Final material-claim adjudication | 1 |
| Bounded repair | 1 |
| Optional specialist stage | 1 |
| Optional model-backed fresh-web discovery | 1 |
| Total possible dispatches | 24 |

Every actual provider-model invocation, including retries and fresh-web wrapper calls, is charged to the same ledger; if a current adapter performs more calls internally, account for them explicitly before admission. The existing separate fresh-web tool/network/time allowances also apply and cannot bypass the job cap. Omit optional work in this order when resources are insufficient: specialist, fresh web, legacy continuation, supplementary planning, nonessential translation, extra topic splits. Translation essential to the selected scope cannot be silently omitted; mark the requirement gap or reject the plan.

Reserve mandatory synthesis and final adjudication before optional work. Redrafts that cannot be admitted leave the affected judgement needs-review rather than reuse an invalidated conclusion. Token reservation uses the frozen model profile's per-call maximum and existing uncertain-call rules, with a total no greater than the existing 256,000 output/reasoning token ceiling; input usage is separately measured. If mandatory reservations cannot fit the configured profile, preflight explains insufficient capacity and does not start doomed work. Do not silently change model or reasoning settings. Add a maximum-work fixture proving both dispatch and token bounds, and interruption cases proving exhausted reservations never reset on resume. A05 applies tier structure within this contract rather than inventing a later budget scheme.

Preflight must show scope, observation dates, horizon, selected requirements, source readiness, likely gaps, approximate total-duration range and what is actually budgeted. Use measured duration distributions after V03; until then say collection allowance plus generation time varies. Show separate model compatibility/capacity messages outside the report product.

Offer at most two short clarification questions only if ambiguity materially changes geography, entity, observation dates or decision need. Supply a visible proposed brief for acceptance/edit. Straightforward questions run without a mandatory clarification detour. Subscription activation needs its required fields resolved once; recurring editions never wait for a new conversational answer silently.

Tests: exact request boundaries, tier-scaled requirement validation, optional omission receipts, no automatic model downgrade, accessible preflight warnings and no expenditure during preview. Provider connectivity tests are explicitly labelled actions and do not run on every form keystroke.

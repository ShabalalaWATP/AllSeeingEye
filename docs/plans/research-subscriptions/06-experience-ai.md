# Packet 6: clear workflows and bounded AI features

Goal: make the improved pipeline easy to use and expose useful analysis without flooding the map, adding team bureaucracy or rebuilding existing exports/chat.

## X01: Research journey and report reader

Dependencies: R01–R04, E01, A03, A05. Ownership: `frontend/src/features/research/`, shared brief controls and report reader components. Use current design tokens/component patterns; apply the relevant frontend skill when implementation begins.

Four concise stages:

1. **Brief:** question or searchable starter, required questions, saved brief choice. Offer clarification only for material ambiguity.
2. **Scope and perspective:** countries/entities/optional saved area, observation dates, optional outlook horizon, lens/audience and language. Distinguish observed period from forecast prominently.
3. **Depth and coverage:** Basic/Deep/Advanced, planned source families/readiness, predicted gaps and budget/duration information. Advanced source/task/private controls expand on demand with clear labels and error summary.
4. **Run:** brief summary, stage progress, usable partial drafts, stop/resume and exact failure action. Normal users do not need model/reasoning diagnostics in the main reading flow.

Keep “Run once”, “Save brief” and “Subscribe” as actions on the same brief. Subscription configuration adds cadence and delivery without retyping the question. Explain private-source disclosure exactly where the choice is made, not buried in a technical panel.

Reader: one coherent report with executive summary, clickable citations, useful contents, clear requirement coverage and material limitations. Small screens get a collapsible contents control. Keep detailed evidence/method/usage panels secondary; visible status never depends on opening them. Support error/retry, empty and partial states.

Accessibility: semantic steps/labels, keyboard operation, focus movement on navigation/errors, reduced motion, adequate contrast in existing themes, flexible widths and no horizontally clipped forms. Retain user choices when navigating back. Do not steal map interactions with permanently open overlays.

Tests: complete custom and preset journeys, back/edit preservation, hidden advanced errors, conversion to subscription, mobile contents and screen-reader labels. Browser visual/keyboard checks at V03 are required in addition to component tests.

## X02: subscription control panel

Dependencies: S05, S06, R03, A04, X01. Ownership: `frontend/src/features/reports/RecurringResearchPage.tsx`, schedule components/hooks, shared API client and relevant user settings.

Provide a concise top summary and a searchable list of subscriptions. Filters: active, paused, needs attention, topic and cadence. A row/card shows title, topic/lens, next local run, last edition quality, coverage interval and current progress. Do not show a wall of technical fields or confuse upcoming cadence with retry time.

Creation reuses the brief editor plus scheduling controls: Daily, Weekly, Monthly, 3 Monthly, 6 Monthly, Annual; preserve existing Weekdays for older/API schedules. Show timezone, DST behaviour and next three occurrences; observation mode; baseline now choice; source readiness; expected monthly usage and limit. Existing subscriptions keep their configured cadence during migration.

Actions: open latest edition, baseline/run now, retry eligible edition, pause/resume, edit, duplicate and archive/delete with confirmation. Display why actions are unavailable. A pending/unknown paid call has an explicit resume/review action, not an ambiguous Retry button.

Edition drawer/page: original due slot, started/finished times, attempts, stage, exact brief revision, selected source coverage, safe error/action, report link, comparison to prior accepted edition, actual/estimated usage. Keep full source/debug receipts in a secondary authorised panel. Show monthly totals only when supported by the usage ledger; do not invent currency values.

Use C04's bounded visibility-aware refresh. A 1,000-row test fixture must remain paginated; never load all old reports just to display subscription status. Refresh must not reset edits or focus. Notifications link to the exact edition; externally configured delivery is opt-in and independent from generation status.

Tests: each control/permission/state, retry versus cadence labels, empty history, long titles, local dates, conflict edits, progress refresh, quiet-period comparison, modal focus and 1,000-summary pagination. Verify both desktop and narrow layouts in V03.

## X03: indicators, forecasts, timelines and corrections

Dependencies: A02, A04, E04. Ownership: focused domain/application modules extending existing claims and monitoring, report/brief panels and canonical figures.

Add a versioned indicator/forecast ledger, not an autonomous prediction scoreboard:

- Forecast: exact claim/version, issued time, horizon, resolution criterion, PHIA likelihood band, confidence dimensions, supporting/contrary evidence, review date and state (open, due, resolved, superseded, unresolved).
- Indicator: observable condition, units/threshold where appropriate, source/capability, expected update frequency, current observed evidence and explicit missing-data behaviour. No source data means unknown, not “condition false”.
- Review: model may suggest an outcome with cited observations; a deterministic unambiguous threshold or an authorised reviewer confirms resolution. Preserve who/what resolved it, evidence and later corrections. Ambiguous outcomes remain unresolved.
- Calibration: show counts and sample limitations; calculate calibration only for sufficiently defined resolved forecasts. Do not turn PHIA ranges into exact probabilities via a hidden midpoint and present spurious precision. If probabilistic scoring requires explicit numeric estimates, retain them as a separately designed evaluated field, not a fabricated conversion.

Build sourced timelines from typed observation/claim records. Each entry carries occurrence/publication dates and uncertainty, entity IDs and passage references. Contradictory event dates can coexist with labels. Corrections append linked entries and alert affected briefs/claims according to existing authorised notifications; they do not mutate old reports.

Render compact tables/timelines in reports and a filterable ledger in supporting research views. Show upcoming review items without adding a new global sidebar page. Link every item back to frozen report/claim/evidence and include relevant records in existing exports.

Tests: event versus publication date, threshold boundary/unit conversion, late correction, unresolved outcome, past horizon, superseded forecast, missing source, permissions and immutable past report. Human label calibration remains a V01/V03 acceptance gate.

## X04: typed quantitative analysis and specialist stages

Dependencies: E03, A02, A05. Ownership: narrow analysis ports/domain calculators, orchestration tool registry and canonical report figure models.

Implement deterministic, allowlisted calculations: absolute/percentage change, indexed series, rolling summaries, selected rates with explicit denominators and comparisons across aligned periods. Inputs must be typed source observations with provenance; preserve units/currency/frequency/seasonal adjustment/vintage. Reject incompatible units, zero denominators, insufficient sample length and silent interpolation. Missing values remain missing.

The model proposes an analysis specification from a fixed schema. A validated tool computes results and returns values, formula/method version, exact inputs, coverage and evidence references. No shell, arbitrary Python/JavaScript, arbitrary SQL or unrestricted URL-fetch capability. Charts are generated from those validated values using existing renderers, with axes/legend/units/source note and accessible table alternatives. Model-generated numbers are not accepted as tool outputs.

Specialist stages use existing orchestration and the same job budget:

| Stage | Distinct work |
| --- | --- |
| Cyber | Link validated product/actor identifiers to advisories, attribution caveats and defensive relevance. Avoid active probes or claimed compromise from loose matches. |
| Economy | Check series comparability, revisions, data-release timing and explicit transmission mechanisms; calculate only supported metrics. |
| Regional/language | Follow authorised original-language documents, preserve translations and distinguish local/party claims from observations. |

Initially permit at most one requested specialist stage per job; it replaces optional work within the existing call budget. If V01 demonstrates a benefit, a separately measured policy revision can expand this. No parallel general-agent debate merely rephrasing the same snippets. Report absent tools/data as a limitation rather than fabricate a chart.

Tests: unit/frequency/currency mismatch, revision vintage, zero/null, malicious tool spec, unsupported operation, exact chart values, staged budget exhaustion and repeat checkpoint reuse. Quality evaluation must compare source-grounded outputs with and without the specialist stage before claiming an improvement.

## X05: report Q&A, aliases and voluntary profiles

Dependencies: R02, A02, X03, X04. Ownership: existing Ask Eye report-context bridge, entity review integration and personal settings/profile modules.

Report Q&A defaults to the selected immutable report version and its authorised evidence. Show the report title/edition in chat. Answers cite exact report claims/passages and may say the report does not answer the question. “Search for newer evidence” is a separate explicit action creating a bounded new research/follow-up job with dates/scope; it does not silently overwrite the frozen report or cite fresh content as if it were in the old edition.

Reuse the current Ask Eye conversation/citation/UI tools and provider assignment. Recheck report and private evidence permissions for every retrieval/release, including a conversation reopened after team access changes. Do not send the entire report history to every answer; use bounded claim/passage retrieval with selected-version filters. No new floating chatbot or competing export flow.

Entity disambiguation: extend existing reviewed entity/candidate registries. Store canonical identifier, aliases/languages, entity type, source, jurisdiction and review state. Propose potential matches; require resolution for ambiguous entities that materially affect a search. Merge/split corrections are versioned and do not rewrite old evidence references. Avoid treating unrelated companies/persons/actors with the same label as one entity.

Voluntary relevance profile: user-selected organisation/sector/countries/technologies/assets from validated public identifiers and optional private descriptions. Defaults empty/private; editable/deletable by the owner; explicit sharing only through existing scope controls. Use it to prioritise relevant questions and defensive implications, not change facts or likelihood. Private profile text cannot become public search terms without an explicit disclosure choice. No automatic network scanning or actions on listed assets.

Tests: exact older-version answer, absent answer abstention, explicit fresh search, private citation revocation, cross-user chat isolation, ambiguous alias, changed canonical entity, profile deletion and private-term leakage. Done when these features add usable context while preserving evidence and privacy boundaries.

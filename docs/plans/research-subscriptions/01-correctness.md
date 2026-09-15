# Packet 1: correctness and truthful states

Read the [entry point](../../RESEARCH_SUBSCRIPTIONS_IMPLEMENTATION_PLAN.md) first. Goal: repair reproduced failures before adding more collection or AI work. Scope is existing behaviour and its tests.

## C01: retain the effective query through ranking

Dependencies: B01. Ownership: backend report collection/selection/query handoff and relevant tests.

Read:

- `backend/src/ase/application/reports/production_collection.py`
- `backend/src/ase/application/reports/production_selection.py`
- `backend/src/ase/application/reports/production_types.py`
- `backend/src/ase/application/reports/research.py`
- `backend/src/ase/domain/research.py`

Implementation:

1. Reproduce the audited case with 30 stale-topic distractors and one direct match to the operator's revised term; Basic retains 24. Cover both a stale direction object and no direction object.
2. Use one explicit effective-query object for collection and selection. Define precedence: validated operator override; accepted runtime revision/translation derived from that override; direction only when no effective query exists; original request as final fallback. Preserve provenance and order of term groups rather than overwriting them with a union of stale terms.
3. Only include admitted supplementary tasks. Respect excluded providers, languages, geography, historical period, private evidence permissions and existing maximum query sizes.
4. Store the exact effective plan in collection checkpoints and coverage receipts. Resume uses that plan; it does not ask the model to reconstruct it.
5. Keep ranking deterministic and stable on ties. A matching unrelated alias must not bypass geography/time constraints. Keyword matches alone must not be called verified relevance.

Tests: add `backend/tests/test_research_effective_query.py` using existing event/job builders. Assert the direct record survives; rejected revisions do not appear; query variants survive a checkpoint round trip; scope restrictions and private-input isolation remain intact. Run existing collection, depth and replanning suites too.

Done: collection, preview and final evidence selection use the same authorised query, with the audited exclusion case prevented.

## C02: outcomes and cosmetic edits

Dependencies: B01. Ownership: existing schedule/report outcome bridge, schedule manager, row state projection and tests.

Read `backend/src/ase/container/features.py`, `application/schedules/runner.py`, `application/schedules/manage.py`, `application/reports/production_version.py`, `domain/schedules.py`, and `frontend/src/features/reports/SchedulesSection.tsx`.

Implementation:

1. Replace the report-ID-only producer return with a typed result including report ID, exact version ID, production outcome, coverage state and safe error code. Reuse current report status enums; do not guess success from a non-null ID.
2. Map failed, needs-review and incomplete coverage to attention in the existing UI immediately. A review-required report can be opened, but is not labelled an unqualified successful edition.
3. Keep failed runs from advancing successful-report baselines/fingerprints. The later S03 task provides full retry timing. Do not add a temporary independent retry loop.
4. Cosmetic edits (name/description) preserve pending due slot, previous baseline and run outcome. Explicit cadence/time edits use a separately tested reschedule path; display their effect before saving.
5. Do not place exception text, provider response bodies or credentials into public error fields. Map stable error codes to helpful UI messages.

Tests: failed saved version, needs-review saved version, partial coverage, production exception, ready complete report, rename of overdue daily schedule, and ordinary rename. Existing monthly/leap-year behaviour must remain unchanged. In S02 remove this synchronous bridge once schedules use durable completion.

Done: report existence cannot masquerade as successful production, and renaming cannot skip a due edition.

## C03: historical and exact-version follow-up

Dependencies: C01. Ownership: report follow-up API/scope conversion and frontend handoff.

Read `frontend/src/features/research/followUpScope.ts`, `FollowUpSummary.tsx`, `ResearchPage.tsx`, `frontend/src/features/reports/ReportPage.tsx`, and the current report-job parent-reference validation.

Implementation:

1. Carry the selected report version, not just the report ID or latest version, into follow-up. Display the parent title, edition and observation dates in the brief summary.
2. Preserve recorded-time start/end and exact area geometry. Editing either creates a new explicit scope with recorded differences; it must not silently switch to present-day research.
3. Reauthorise access to the exact parent and every reused private source. Use immutable evidence references; do not fetch private assets merely from copied IDs.
4. If an existing parent type cannot yet round-trip, hide the broken submit path and explain the limitation beside the action until this task supports it. Do not leave Retry as a supposed fix for invalid scope.
5. Persist the resulting handoff using the existing request representation now; R02 adapts it to Research Brief without changing the behaviour.

Tests: historical non-area report, area report, selected older version, edited time range, inaccessible parent, deleted/disabled input, and backward-compatible report links. Run `followUp.test.tsx`, `areaResearch.test.tsx`, report publication and report-job scope tests.

Done: a user can follow up a supported selected version without losing scope; unsupported objects cannot offer a button that always fails.

## C04: immediate feedback and accessibility fixes

Dependencies: C02, C03. Ownership: current Research/Subscriptions forms and report drawer interaction only.

Implementation:

- Use the app's existing polling/query approach to refresh visible subscription/job summaries. Start with 5 seconds while active work exists, 30 seconds while idle, pause while hidden, back off on failure and cancel on unmount. Do not fetch entire evidence packets to update rows.
- Show a top-level error summary linked to invalid fields, including collapsed advanced settings. Expand and focus the first invalid group on submit.
- Selecting Edit brings the form into view and focuses its heading/first field; closing restores focus to the invoking row.
- Give deletion a named confirmation with impact or an undoable archive, following current project patterns. Do not change data-retention policy through a UI convenience.
- Correct the report workspace focus loop to include reachable `summary` elements and exclude hidden ancestors. Escape and close restore focus. Use a proven existing focus utility if available.
- Add visible retry controls for failed initial report/subscription loads. Preserve loaded results during transient refresh errors.

Tests: fake-timer refresh/visibility/cleanup, advanced error navigation, editing from below the fold, keyboard drawer loop and permission-denied refresh. Manually verify keyboard behaviour at V03; jsdom is insufficient evidence for actual layout.

Done: the user sees current states and actionable errors without having to reload, hunt for invisible fields or escape a broken focus trap.

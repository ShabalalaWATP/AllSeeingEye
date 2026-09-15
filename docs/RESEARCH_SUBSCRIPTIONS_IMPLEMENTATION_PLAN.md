# Research and Subscriptions: approved implementation plan

Date: 14 September 2026. Status: **implementation in progress; see the execution log for verified milestones**.

This is the execution entry point for a smaller coding model. It translates the accepted [Research and Subscriptions audit](RESEARCH_AND_SUBSCRIPTIONS_AUDIT_2026_09_14.md) into bounded tasks. The audit is the evidence for the defects, while this document specifies the proposed behaviour. Numbers described as initial policy below are design decisions to evaluate, not measured performance or doctrine.

The complete scope includes reliability repairs, shared briefs, topic presets, better acquisition, evidence assessment, professional reports, dependable subscriptions and the additional AI features. Finishing the reliability phase does not finish this plan. Implementation is authorised by the user's acceptance; deployment, purchases and external delivery still follow the session's applicable approval rules.

## 1. Read order and task packets

Read this entry point, the packet for the next task and only the relevant implementation files. Do not load the entire repository or every historical plan into each model context.

| Order | Packet | Result |
| --- | --- | --- |
| 0 | This document, B01 | Baseline, ownership and regression inventory |
| 1 | [Correctness](plans/research-subscriptions/01-correctness.md), C01–C04 | Relevant evidence retained; truthful outcomes and working follow-up |
| 2 | [Durable subscriptions](plans/research-subscriptions/02-durable-subscriptions.md), S01–S06 | One execution engine, immutable editions, retries, catch-up and history |
| 3 | [Shared briefs](plans/research-subscriptions/03-briefs-and-presets.md), R01–R04 | Configure once, run or subscribe, with structured lenses; complete E00 after R02 and before R03 |
| 3a | [Preset specifications](plans/research-subscriptions/PRESETS.md) | Twenty editable starting briefs, not just country labels |
| 4 | [Source and evidence collection](plans/research-subscriptions/04-source-evidence.md), E00–E05 | E00 supplies the early capability contract; E01–E05 add relevance, original passages, history and contrary searches |
| 5 | [Assessment and report product](plans/research-subscriptions/05-assessment-reports.md), A01–A05 | Stronger claim support, doctrine enforcement, meaningful changes and exports |
| 6 | [User experience and AI tools](plans/research-subscriptions/06-experience-ai.md), X01–X05 | Clear control panels, coverage, indicators, calculations and report Q&A |
| 7 | [Validation and release](plans/research-subscriptions/07-validation-release.md), V01–V04 | Reproducible quality, operational, browser and export acceptance |

## 2. Preserve the existing foundation

The app already has durable one-off report jobs, staged synthesis, explicit collection budgets, private evidence, multilingual queries, an evidence/claim ledger, source provenance, PHIA vocabulary, confidence ceilings, report exports, calendar recurrence and subscription fingerprints. Extend those systems. Do not create a competing queue, report renderer, model administration page, doctrine engine or separate subscription research pipeline.

The Ask Eye improvements from earlier work are also an existing integration point, not a blank slate. Keep the present Map/Research/Subscriptions/Geolocation navigation and separate administrator permissions. Do not turn this work into another map redesign or team-management expansion.

Existing reference documents:

- [Durable research jobs](DURABLE_RESEARCH_JOBS.md).
- [Automatic research planning](AUTOMATIC_RESEARCH_PLANNING.md).
- [Evidence scoring](REPORT_EVIDENCE_SCORING.md).
- [Professional report product](PROFESSIONAL_REPORT_PRODUCT_PLAN.md).
- [Architecture](01_ARCHITECTURE.md) and [doctrine/reporting](03_DOCTRINE_AND_REPORTING.md).

## 3. Non-negotiable implementation rules

1. Read global, repository and nested instructions before writing. Use current code as the baseline; audit line numbers may drift.
2. One editing owner per task. If agents are available and authorised, delegate bounded review or disjoint work with explicit ownership. Never revert another worker's edits. At plan creation, unrelated Ukraine feature files were being edited in the working tree.
3. Add the behavioural regression first for a reproduced defect when practical. Keep fixtures offline and deterministic; live provider and model acceptance is separate.
4. Keep source files near 350 lines and split touched oversized files by responsibility. Generated API contracts and migrations are exceptions. Do not move unrelated code to satisfy a line count.
5. Keep routes thin, business rules in application/domain modules and storage in adapters. Shared frontend briefs belong in components/lib/hooks rather than importing one feature's internals into another.
6. Reuse current authorisation, safe HTTP, source-disable guards, parser isolation, encrypted credentials and final-release checks. Briefs, jobs, evidence, reports and history always retain owner/team scope.
7. Model suggestions cannot expand authorised geography, export private terms to public search, invent source identifiers, raise spending limits or change provider credentials. Generated prose is never independent evidence.
8. Preserve exact frozen report versions. New grading, presets, source corrections or a changed model must not silently rewrite old reports.
9. Distinguish collection operations, underlying HTTP requests, LLM requests, output/reasoning tokens, input tokens and currency estimates. Do not call them all “tokens” or “sources”.
10. Preserve uncertain-call accounting: an interrupted paid call whose outcome is unknown must not be automatically replayed. Unattended does not mean unlimited retry.
11. No new production dependencies unless an existing capability cannot meet an identified requirement. No new generic agent framework or arbitrary code-execution tool.
12. Update only task-owned documentation. Do not claim current live acceptance using old development results. Do not commit, push or deploy just because this checklist exists.

## 4. B01: baseline and implementation ledger

Dependencies: none. Ownership: task evidence, regression fixtures and execution ledger only.

- Record branch, HEAD and `git status --short`, without printing environment values or credentials.
- Read the relevant audit section and identify the current function/component implementing it. If another change already fixes it, prove it with a regression and record the evidence rather than applying the old patch mechanically.
- Inspect current Alembic heads before allocating any migration. Do not assume the next revision is 0035. Never migrate the operator database as part of test setup.
- Run the focused suites from the validation packet to establish current failures. Record unrelated failures separately and preserve them.
- Add a task ledger at `docs/plans/research-subscriptions/EXECUTION_LOG.md` when implementation starts. Capture exact commands, results, changed files, remaining blockers and the next task.
- Establish representative offline evaluation fixtures before changing ranking and assessment. V01 specifies the corpus; human labels must remain pending until supplied by an actual reviewer.

Done when the baseline is reproducible, active file ownership is known and C01 has a failing test or verified pre-existing fix. A missing external provider does not prevent local work.

## 5. Sequence, dependencies and completion register

Execute in the listed order by default. Cross-packet dependencies are explicit in each task. C02 is an immediate compatibility repair and is later absorbed by S02; do not retain two success-state implementations. S01 initially snapshots the current request and R01 later attaches the canonical brief revision using a versioned adapter.

The only deliberate early jump is E00 (capability inventory contract) after R02 and before R03. It requires no new connectors. Later E03 implements missing bridges and live checks, so preset validation does not depend on unfinished connector work.

| State | ID | Task |
| --- | --- | --- |
| Complete | B01 | Baseline, regressions and execution ledger |
| Complete | C01 | Carry effective query into final ranking |
| Complete | C02 | Truthful subscription outcomes and safe cosmetic edits |
| Complete | C03 | Exact-version, historical and area follow-up |
| Complete | C04 | Immediate form/status/accessibility repairs |
| In progress | S01 | Edition ledger and additive migration |
| Complete | S02 | Durable enqueue, completion and authority checks, with two-edition worker regression |
| In progress | S03 | Retry and recovery pass; monthly budget integration under test |
| In progress | S04 | Timezones, due slots, overlap and catch-up under final integration checks |
| In progress | S05 | History, run-now, edition controls, pause/resume, accepted baseline, in-app events and paused copies of ordinary and exact-revision brief subscriptions implemented; notification policy and delivery acceptance remain |
| In progress | S06 | Independent scheduler startup, bounded fair due batches, safe source-failure diagnostics and feed-disabled restart test implemented; broader recovery and operations acceptance remain |
| In progress | R01 | Canonical versioned Research Brief, persistence, API and one-off admission pass; subscription parity remains |
| In progress | R02 | Shared brief editor and report/map handoff under test; subscription admission remains |
| Complete | E00 | Offline capability contract and typed bundle resolution |
| In progress | R03 | All 20 backend presets and the frontend picker validated offline; browser and live-readiness checks remain |
| In progress | R04 | Exact saved-brief preflight under implementation; depth contract still pending |
| In progress | E01 | Deterministic allocator, persisted initial phase reservations and frozen fresh-web allocation implemented; full post-draft source budget enforcement remains |
| In progress | E02 | Guarded selected-original follow-through, durable source reservation, frozen passage and authorised exact-version read implemented; reviewed policy configuration, broader item mapping and correction governance remain |
| In progress | E03 | Typed Radar, ONS, ECB and opt-in IODA research bridges pass offline contracts; narrow live API shape probes pass for ECB/IODA, but wider provider/readiness and usage review remain |
| In progress | E04 | Selected USGS subscription index, bounded incremental acquisition, cursors and receipts implemented; broader permitted-source retention, corrections and long-interval acceptance remain |
| In progress | E05 | Bounded post-draft challenge integration, lease-fenced source receipts and restart recovery pass focused tests; whole-stage budget and wider challenge coverage remain |
| In progress | A01 | Claim-scoped grading, authorised reviewer history and opt-in exact-version reviewed assessment in reader/exports implemented; automatic production scoring and reviewer UI remain |
| In progress | A02 | Final post-challenge doctrine validation now gates release and requires Needs review on errors; typed forecast fields and exact frozen passages remain unavailable to production checks |
| In progress | A03 | Citation/challenge review gate and frozen document warnings landed; full adjudication pending |
| In progress | A04 | Six-state exact-edition comparison and ambiguous-claim mapping review are persisted and shown in history; semantic verification and notification policy remain |
| In progress | A05 | Tier-scaled synthesis structure and requirement accounting pass focused tests; whole-stage budget and qualitative acceptance remain |
| In progress | X01 | Four-step Brief–Scope–Depth–Run journey and mobile report contents pass focused tests; browser acceptance remains |
| In progress | X02 | Subscription control panel, history, activity and budget visibility implemented; full workflow and delivery UX remain |
| In progress | X03 | Exact reviewed-claim forecast/indicator ledger API, persistence and migration pass focused tests; later-outcome evidence, numerical readings, automation and UI remain |
| In progress | X04 | Bounded allowlisted quantitative core passes focused tests; report-job orchestration, charts and specialist stages remain |
| In progress | X05 | Exact-version frozen-report Ask Eye answers and private saved/resumed chats pass focused tests; entity aliases and relevance profiles remain |
| In progress | V01 | Frozen 60-case synthetic corpus and deterministic checks pass; independent human labels and model quality runs remain |
| In progress | V02 | Focused integration, static checks and dependency audits pass; full suites and populated PostgreSQL/recovery acceptance remain |
| In progress | V03 | Narrow live source-shape probes and isolated authenticated browser smoke pass; current model, complete browser journeys and rendered exports remain |
| In progress | V04 | Durable-jobs, schedule API, operations, security and acceptance records updated; rollout and final evidence remain |

Use Pending, In progress, Blocked with reason, or Complete with evidence. A fixture-tested connector with missing credentials is not live accepted. A pending human-quality gate is not an implemented feature failure, but it prevents claiming complete operational acceptance.

## 6. Coverage of the accepted audit

| Accepted finding or recommendation | Tasks |
| --- | --- |
| Explicit terms lost; fixed provider ordering | C01, E01 |
| Frozen-only challenge in durable Deep/Advanced | E05, A02 |
| Failed/review subscription shown as successful | C02, S02, A03, X02 |
| Annual failure, missed windows, rename and duplicate work | C02, S01–S04 |
| Feed-switch coupling and revoked-authority silence | S02, S06 |
| Material challenge/citation warnings absent from final product | A02, A03 |
| Historical/selected-version/area follow-up | C03, R02 |
| Basic/Deep/Advanced structure and output exhaustion | R04, A05 |
| Headline-only research; no primary follow-through | E02 |
| Source catalogue versus actual connected/eligible/attempted coverage | E00, E01, E03, R04 |
| Long-interval subscriptions cannot recover old RSS | E04, S04 |
| Structured economy/cyber/map source use | E03, X04 |
| Doctrine, forecast horizons, claim adjudication and source independence | A01, A02, X03 |
| Shared brief, output preferences, map scope and requested viewpoint | R01, R02, R04 |
| Cyber/economy/conflict presets and personal saved briefs | R03, PRESETS.md |
| Baseline/run/retry/pause/history/timezone/budget/delivery | S03–S05, X02 |
| Novelty versus changed assessment and corrections | A04 |
| Brief clarification, gap planning and bounded agentic tools | R04, E01, E05, X04 |
| Requirement matrix, timelines, indicators and forecast review | A05, X03 |
| Report Q&A, entity disambiguation and voluntary profiles | X05 |
| Visual/form/status/mobile/keyboard improvements | C04, X01, X02 |
| Quality, live operation, cost, recovery and honest limitations | V01–V04 |

## 7. Starter prompt for the implementing model

> Implement the approved Research and Subscriptions plan in `C:\AlexDev\OSINT\docs\RESEARCH_SUBSCRIPTIONS_IMPLEMENTATION_PLAN.md`. Read applicable instructions, inspect current git status, and start with the first task not evidenced as complete. Read only its task packet and relevant code. Preserve other workers' changes. Implement a bounded milestone, add meaningful regressions, run the relevant checks, and update the execution ledger and task status with exact evidence. Keep following dependencies across milestones; do not mark the whole plan complete after an early phase. Preserve existing security, immutable evidence and uncertain paid-call safeguards. If a provider, human label or environment is unavailable, finish independent work and record the specific unverified acceptance item. Do not invent credentials, weaken tests or substitute simulated data for live acceptance.

## 8. Handoff template

Use this compact entry after each milestone or before context loss:

```text
Task ID and status:
Baseline branch/HEAD and unrelated changes:
Behaviour changed and owned files:
New or updated contracts/migration:
Commands actually run and results:
Security/permission/recovery cases verified:
Unverified live, human or browser gates:
Known issue and exact next action:
Next task ID and dependencies:
```

No application code, database, source connection or provider setting is changed merely by generating this plan.

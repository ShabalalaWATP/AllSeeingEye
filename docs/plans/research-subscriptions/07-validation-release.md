# Packet 7: validation, measured quality and release

Use this packet from B01 onward. Passing unit tests proves bounded behaviours, not source truth or current provider reliability. Historical audit results are baselines, not acceptance evidence for newly implemented code.

## V01: evaluation corpus and quality measurements

Dependencies: start fixtures at B01; final evaluation after A05/X05. Ownership: existing `backend/evaluations/` harness, new fixture manifests and evaluation reports.

Create at least 60 independently reviewable cases, ten each for conflict, cyber, economy, disaster/humanitarian, company/policy and custom-area research. Reuse useful existing synthetic fixtures, but label synthetic versus captured public evidence and model versus human judgements accurately. Each case has a question/requirements, source packet, allowed scope/time, expected useful sources/passages, known pitfalls, acceptable abstentions and reference outcomes. Split development and held-out sets before tuning ranking/prompts.

Include syndicated/translated claims, old stories republished as new, ambiguous entities, contradictory official statements, weak versus strong sources, missing passages, false numerical units, forecasts without horizons, quiet periods, revisions at the same URL, failed providers, partial dates and privacy-sensitive inputs. At least 12 cases compare consecutive subscription editions including probability-only change and no-data periods.

Two separate result tracks:

1. Deterministic contract/regression evaluation, runnable offline in CI.
2. Human-reviewed analytical evaluation of current configured-model output. Automated graders may assist but cannot be described as independent human labels. Record reviewer identity/role, disagreements and rationale. Where possible use a second reviewer for consequential disagreement.

Measure per domain and depth: required-question coverage, retrieval recall against the curated available packet, passage support, date/attribution/number accuracy, counterevidence retention, appropriate abstention, duplicate/origin handling, meaningful change detection, latency, requests and known/estimated cost. Do not use article count, report length or self-assigned confidence as an accuracy metric.

Initial engineering acceptance targets, to be reviewed against the labelled set rather than claimed as doctrine:

| Measure | Initial release gate |
| --- | --- |
| Citation identifiers and exact-version references | 100% valid on fixture corpus |
| Required questions accounted for | 100% have answer/partial/disputed/gap state; no silent omissions |
| Privacy, authorised scope, budget and duplicate-publication invariants | Zero failing deterministic cases |
| Material counterevidence in known fixtures | 100% retained or an explicit unsupported-acquisition gap |
| Passage-supported material claims | At least 95% judged supported or appropriately qualified on labelled cases; no unflagged high-consequence contradiction |
| Date/attribution/number accuracy | At least 95% on reviewed material items, report counts and denominator |
| Curated relevant-source recall | Improvement over B01 with no domain regression left unexplained; do not invent a whole-web recall percentage |
| Subscription change precision/recall | Report both on labelled pairs; target at least 90% each before automatic material-change claims are enabled broadly |
| Abstention and missing coverage | All designed no-data cases disclose the gap; no “nothing happened” inference |

If human labels/model runs are unavailable, mark this gate unverified and continue deterministic work. Never manufacture labels or lower a failing threshold to report success. Small samples need counts and uncertainty; they do not establish global calibration. Keep unsupported automation in review-required mode until its quality gate is met.

## Focused commands and tooling

Run commands from the named directory, individually. Discover new task tests with `rg --files` and add them to the relevant selection. These are examples grounded in current repository tooling; check CI again before final acceptance.

**Required local database preflight:** the current backend fixture honours `ASE_TEST_DATABASE_URL` and calls `drop_all`. Before any copied pytest command, use a dedicated test PowerShell session and run the following process-local overrides. They neither change the user's persistent environment nor print database URLs. Keep PostgreSQL acceptance in a separate explicitly disposable environment.

```powershell
$env:ASE_DATABASE_URL = 'sqlite+aiosqlite://'
$env:ASE_TEST_DATABASE_URL = 'sqlite+aiosqlite://'
$env:ASE_TOKEN_RACE_TEST_URL = $null
$asePostgresTestKeys = @(Get-ChildItem Env: | Where-Object { $_.Name -match '^ASE_.*_POSTGRES_URL$' } | Select-Object -ExpandProperty Name)
foreach ($aseTestKey in $asePostgresTestKeys) {
    [Environment]::SetEnvironmentVariable($aseTestKey, $null, 'Process')
}
if ($env:ASE_TEST_DATABASE_URL -ne 'sqlite+aiosqlite://') {
    throw 'Refusing local tests without the disposable SQLite override.'
}
```

At B01, verify current test environment hooks with `rg` before executing: add any newly introduced database hooks to this preflight. Tests must not load an operator database through another setting. For PostgreSQL, use a newly created test database/container and a dedicated test role, validate the exact host/database against its test-provisioning manifest and reject unknown targets before pytest. Do not rely on a name merely containing “test”, and never echo credential-bearing URLs. Fixture-only PostgreSQL gates are skipped in the local SQLite run and must be run separately before PostgreSQL acceptance is claimed.

Backend, `C:\AlexDev\OSINT\backend`:

```powershell
uv run pytest tests/test_research_collection.py tests/test_research_depth.py tests/test_research_replanning.py --no-cov -q
uv run pytest tests/test_schedules.py tests/test_schedule_research.py tests/test_schedule_monthly.py tests/test_schedule_changes.py tests/test_osint_subscriptions.py --no-cov -q
uv run pytest tests/test_warning_scope_background.py tests/test_prepared_report_jobs.py tests/test_report_job_snapshots.py tests/test_report_job_service.py tests/test_report_job_checkpoints.py tests/test_report_job_budget_cancellation.py tests/test_report_job_model_calls.py --no-cov -q
uv run pytest tests/test_doctrine.py tests/test_citation_checks.py tests/test_citation_check_integration.py tests/test_report_document_assessment.py tests/test_report_documents.py --no-cov -q
uv run pytest tests/test_report_sections_contracts.py tests/test_report_sections_planning.py tests/test_report_sections_runner.py tests/test_report_synthesis_steps.py tests/test_report_section_quality.py tests/test_fresh_web_research.py --no-cov -q
```

Frontend, `C:\AlexDev\OSINT\frontend`:

```powershell
pnpm exec vitest run src/features/research/followUp.test.tsx src/features/research/researchTiers.test.tsx src/features/research/areaResearch.test.tsx
pnpm exec vitest run src/features/reports/schedules.test.tsx src/features/reports/schedules.states.test.tsx src/features/reports/subscriptions.test.tsx src/features/reports/subscriptions.edges.test.tsx src/features/report-jobs/ReportJobPage.test.tsx
```

Focused backend commands deliberately use `--no-cov`; report that coverage was not measured. Full suites below retain existing gates. If uv/node access fails because of the execution sandbox, request a scoped command escalation with its stated reason rather than editing runtime variables or weakening isolation. Stop after repeated non-progress as required by project instructions, record the exact blocker and complete independent tasks.

API changes: use the existing CLI procedure from `Justfile`: from `backend`, run `uv run ase export-openapi ../frontend/src/lib/api/openapi.json`; from `frontend`, run `pnpm gen:api`. Recheck the procedure if the CLI has changed. Do not hand-maintain generated TypeScript definitions or run the normal app with live feeds just to obtain a schema.

## V02: integration, migrations, security and recovery

Dependencies: all implementation tasks affecting the tested path. Ownership: integration fixtures, migration acceptance, review evidence and performance harness.

Run the complete existing checks without lowering thresholds:

```powershell
# From backend
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run lint-imports
uv run pytest
uv run bandit -r src -q -c pyproject.toml
uv run pip-audit
```

```powershell
# From frontend
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm audit --audit-level high
```

Also run repository hooks, secret scanning and applicable current CI jobs, including configured Semgrep/container checks where this change affects them. Record unavailable infrastructure separately. Do not claim a full security audit solely from Bandit or a package audit. Focus defensive review on new durable authority paths, query privacy, SSRF, parser resource limits, outbox destinations, IDOR, exports and untrusted model tool specifications.

Database gates on disposable SQLite and PostgreSQL:

- Upgrade from populated pre-change schemas and current head; repeated upgrade no-op; historical reports/schedules preserved.
- Unique edition/admission races across independent sessions, fenced late writes, budget reservation races and transactional final publication.
- Interrupt after every durable boundary: before/after enqueue, provider reservation/dispatch/receipt, passage freezing, synthesis, report commit and outbox acknowledgement.
- Recover with correct known-completed reuse and unknown-call pause. No duplicate stored edition or paid-stage replay attributed as safe.
- Revoke user/team/source/model authority during every release-sensitive path.
- Test real PostgreSQL concurrency and migrations explicitly; a skipped environment-dependent suite is not a pass.

Performance: create realistic fixture payloads (large accepted evidence packet, 1,000 subscription summaries/history pages, retained-index cap). Measure UI summary response latency, memory, queue fairness and worker responsiveness against B01 on the same machine. Initial target: no material regression in p95 summary/list latency or peak process memory beyond 10% without documented cause/approval; no repeated long main-thread tasks above 200 ms in the tested interaction. Do not enforce these through brittle timing unit tests; use a recorded repeatable benchmark. Store original measurements, hardware/runtime and confidence limits.

Owner checks must pass even in partial/retry/history paths. Offline tests use fake model/source adapters, not real keys. No operator database destructive tests.

## V03: current live and user-facing acceptance

Dependencies: V01 fixture readiness, V02. Ownership: documented read-only provider/model smoke tests, local browser journeys and rendered export inspection.

Provider acceptance matrix: each currently configured integration used by a preset gets a minimal current request, status, UTC test date, result count, date/geography granularity and limitations. Test missing/invalid/expired credentials through fixtures, not by altering live credentials. Distinguish working API, empty legitimate result, rate limit, blocked/unavailable and unconfigured. Missing required provider access remains an operational gap; do not mark it successful from a stored key.

Model acceptance: use the current authorised provider/model settings and an explicit bounded run budget. Run representative conflict, cyber, economy, disaster, company and AOI jobs with public test questions. Include Basic/Deep/Advanced and one staged retry/continuation case. Record stage count, latency, model usage and output quality against the labelled cases. Do not silently lower the chosen reasoning level or change models to hide output exhaustion. Provider/model details belong in the acceptance evidence, not exported report prose.

Subscription acceptance: create disposable local test subscriptions, generate a baseline, execute a subsequent edition, verify a meaningful change and a quiet-period result, then exercise pause/resume and known-failure retry. Use fake-clock integration tests for long cadences and DST; do not wait months or claim a simulated run was a live annual observation. Test feeds-disabled scheduling and browser-closed job completion.

Browser checklist at desktop 1440×900, smaller desktop 1280×720 and narrow/mobile width around 390 px, using the actual local app:

- Research custom/preset, all depth choices, period/horizon, language/lens, scope and advanced field validation.
- Save brief, run once, subscribe, exact-version/historical/map follow-up.
- Subscription baseline/run/retry/pause/resume/edit/duplicate/history, due versus retry time, source gap and budget messages.
- Progress survives navigation; refresh pauses when hidden; no form reset; no duplicated request on double-click.
- Keyboard-only navigation, focus restoration, readable contrast, reduced motion and no clipped controls.
- Report citations, mobile contents, Q&A selected version, clear fresh-search action and revoked private access.

Export acceptance: produce one normal, one needs-review and one partial/quiet-period report through the real renderer in Word, PDF and Markdown. Include a table, chart, non-English passage, long URL, multiple-page reference list and significant challenge/citation warning. Use the documents/PDF skills when generating or inspecting those artifacts. Render and visually inspect pages for overflow, repeated headings, captions, working citation references and status placement. The same selected version must produce the same substantive findings across formats.

If a necessary live run would exceed current authorised expenditure or an external channel lacks explicit authorisation, prepare the concrete test and request only that missing permission. Existing authorisation does not need to be asked again. Do not send test messages to other people as a side effect.

## V04: rollout, documentation and completion

Dependencies: V01–V03; blocked external gates remain named and incomplete. Ownership: operating docs, changelog/execution ledger and release evidence.

Update the existing durable-jobs, automated-research, source operations, report scoring, subscription API and security/architecture docs to match implemented behaviour. Supersede obsolete statements about direct scheduled generation and frozen-only challenge. Preserve historical development records as history. Record new retention/data-boundary and calendar/retry decisions in ADRs.

Rollout sequence:

1. Verify additive migrations and backward reads on disposable databases; create an operator backup/restore plan before any authorised real migration.
2. Deploy only through the separately authorised existing workflow. Keep new subscription dispatch behind a default-off rollout setting until schema/backfill and authority/budget checks are accepted. Never enable old and new dispatchers simultaneously.
3. Trial a small set of approved local subscriptions. Observe queue lag, unknown calls, duplicate protection, source gaps and report review rate.
4. Enable additional presets/structured sources as their capability and quality gates pass. Advertise unsupported features as unavailable rather than silently substituting sources/data.
5. Rollback stops new dispatch; retain new edition/job/report data and additive schema. Use a compatible prior build or forward repair. Do not drop new tables or re-enable synchronous generation for slots already admitted.

Produce `docs/plans/research-subscriptions/ACCEPTANCE.md` during implementation with code snapshot, commands/results, coverage, migration DBs, provider matrix, quality denominators, browser/export artifacts, cost/latency, security review and outstanding manual gates. Update the main register and development story honestly. No app implementation is complete merely because its docs are written.

Final completion requires every accepted task accounted for, no unresolved critical regression, passing current required CI, preserved security/access/budget invariants and explicit evidence for operational/quality claims. Report remaining unavailable providers or human-review gates plainly rather than declaring worldwide exhaustive research.

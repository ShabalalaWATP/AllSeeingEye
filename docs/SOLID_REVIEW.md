# SOLID review and remediation plan

Reviewed 20 September 2026 against commit
`6f4d2757f0963af9905ddee4479870fb0ef381da`.
Status: the seven remediation slices below are implemented on
`codex/solid-review-plan`. The original assessment and line references describe
the reviewed baseline; they are retained as the rationale for the changes.

## Implementation outcome

- Model adapters share safe, non-retryable output-exhaustion handling. Regression
  tests first reproduced two calls for Chat Completions and Bedrock; all three
  gateway paths now stop after one call and retain validated accounting only.
- Side-effect-free factory imports and owned lifecycle stacks unwind partial
  startup and continue cleanup after failures. Admission stops before consumers;
  digest cancellation drains before its clients/database close.
- The three private-record API slices use application services and repository
  ports. Dependent report-job/preflight routes also stopped importing persistence.
- Subscription admission, preparation, recovery and fair polling moved into the
  application behind transaction/queue ports. Report stages are assembled in the
  container and injected into the use case.
- Thirty-one provider classes expose typed capability metadata. A shared
  decorator preserves metadata and optional behaviour, with one conservative
  legacy compatibility boundary.
- Frontend feature imports are enforced using TypeScript-aware ESLint resolution,
  including type/re-export/dynamic imports and static template literals. Shared
  presentation and scope policy moved out of individual features.
- Form policy and transitions are pure functions with narrower component inputs.
  Map scenes consume ordered groups, use honest layer types and narrow camera
  capabilities, and separate infrastructure filtering from rendering.

No schema migration or runtime dependency was added. Regenerating OpenAPI from
both the baseline commit and the changed code produced identical schemas. The
checked-in schema has unrelated pre-existing photo-schema drift, which this change
does not silently regenerate.

Residual coupling is explicit: five legacy subscription read projections remain
on the API/persistence exception list; separate container subscription publication,
manual control and retry workflows remain outside the admission extraction. The
review's 7/10 is the historical baseline, not an automatic post-change score.

Focused validation passed for model adapters, lifecycle, API scope/release,
provider wrappers, report continuation/accounting, subscription admission and
frontend behaviour. Seventeen subscription PostgreSQL tests passed against a
separate disposable database. Independent reviews checked behavioural and access
boundaries; their digest-drain and static-template-import findings were fixed.
Backend lint, formatting of all source/test/migration files, strict typing, all
three import contracts, Bandit and the frontend production build passed. Root
script tests passed (42 passed, one POSIX-only skip on Windows).

The repository-wide `ruff format --check .` command hit a local Ruff panic while
traversing existing inaccessible temporary directories. Explicit source, test and
migration roots passed (2,264 files); clean-checkout CI is the full-tree check.
Final full-suite and CI evidence is recorded on the pull request. No production
deployment is part of this implementation. The CLI factory-import change touches
a manually gated deployment path, so a later production release needs the existing
reviewed manual procedure; the deployment guard has not been weakened.

## Assessment

**Overall: 7/10.** The architecture has useful ports, dependency injection,
framework-free core layers and meaningful test seams. Targeted improvements are
justified; a rewrite or dependency-injection framework is not.

These are qualitative engineering judgements, not compliance percentages or
automatically measured quality scores. This review combined repository-wide
structural checks with focused backend, frontend and composition reviews. It is
not a line-by-line audit of every implementation or a security assessment.

| Principle | Rating | Assessment |
| --- | --- | --- |
| Single responsibility | 6/10 | Most modules are focused, but report construction, some HTTP routes, subscription admission and complex forms combine independently changing responsibilities. |
| Open/closed | 7/10 | Feed/model ports support extension; implicit provider metadata and repeated map-layer wiring increase the changes needed for new capabilities. |
| Liskov substitution | 6/10 | Typed seams and substitution tests exist, but model adapters disagree on explicit token-exhaustion semantics. Some map/provider contracts are weaker than their consumers expect. |
| Interface segregation | 7/10 | Many small ports are useful. Whole-container dependencies and entire form-state contracts expose more than some consumers need. |
| Dependency inversion | 8/10 | Backend core layering is enforced. SessionBridge and MapEngineFactory are good frontend examples. Some routes and container workflows still depend directly on persistence details. |

The overall score is rounded from these assessments. Small files, many protocols
and passing type checks alone do not establish SOLID adherence. A composition root
necessarily knows concrete implementations; the concern is business execution
inside it, not its use of concrete constructors.

## Evidence and findings

### 1. Model substitution changes exhaustion handling

Priority: high. Principles: Liskov substitution and single responsibility.

The port documents `LlmTokenBudgetExhausted` as a non-transient outcome that must
not repeat the same budget (`application/ports/llm.py:62`). OpenAI Responses raises
that exception for its explicit output-limit signal
(`adapters/llm/openai_responses.py:114`). Chat Completions `finish_reason=length`
and Bedrock `stopReason=max_tokens` instead raise generic `LlmGatewayError`
(`adapters/llm/openai_compatible.py:132`, `adapters/llm/bedrock.py:100`).

`application/reports/drafting.py:127` stops for the specific exception, but its
generic handler at line 137 continues the two-attempt loop. An offline parser
reproducer confirmed the exception-class difference. The resulting retry risk
follows from the call path; no live billed request was made to reproduce it.

Remedy: normalise explicit exhaustion signals to the port's existing exception,
retain validated usage metadata, and add shared adapter/caller contract tests.
Do not infer exhaustion from arbitrary error messages or suppress legitimate
transient retries.

### 2. Resource lifecycle lacks reliable failure unwinding

Priority: high. Principles: single responsibility and explicit resource ownership.

`main.py:28` starts workers before entering the cleanup-protected `try` at line
40. A startup exception can bypass that cleanup. Both its stop sequence and
`container/lifecycle.py:14` perform sequential cleanup in which an exception can
prevent subsequent cleanup. `main.py:91` constructs an application on import;
`cli.py:39` imports its factory through that module.

These are control-flow findings, not a reproduced production incident. Use an
explicit lifecycle owner, such as a small `AsyncExitStack` integration, registering
cleanup as resources become owned. Unwind on partial startup and continue cleanup
when one resource fails. Separate factory imports from ASGI instance creation,
preserving `ase.main:app` and existing deployment behaviour.

### 3. Some routes own persistence and business policy

Priority: medium. Principles: single responsibility and dependency inversion.

`api/routers/research_briefs.py:55` constructs SQL; line 85 builds latest-revision
queries; later code handles owner/revision policy and commits. It imports a
private persistence decoder. `api/schemas_research_briefs.py:154` accepts an ORM
row. `api/routers/assistant_history.py:108` and
`api/routers/original_passages.py:31` contain similar workflow coupling.

Extract application use cases, focused repository methods and result DTOs one
vertical slice at a time. Preserve SQL visibility filtering before limits and
the exact session, authorisation, commit and response-release checks. Existing
import-linter contracts allow API-to-adapter dependencies, so their success does
not detect this boundary erosion.

### 4. Wiring and application workflow are intermingled

Priority: medium. Principles: single responsibility, dependency inversion and
interface segregation.

`container/subscription_enqueue.py:49` implements subscription admission; its
constructor takes the whole container. Lines 66 onwards combine idempotency,
enablement rules, SQL reads, guarded admission and rollback. Related preparation,
catch-up and control modules extend this execution path.

`application/reports/generate.py:68` accepts 32 collaborators/options and constructs
several report helpers internally. That combines report orchestration with object
graph construction. Do not hide the same dependency set in an untyped bag.

Move subscription decisions/orchestration into application services and database
transactions into focused adapters. Assemble report stages in container factories.
Retain the documented container package/mixin shape; progressively narrow inputs
where execution currently receives the whole container. The 15 wiring mixins are
not by themselves a substitution defect.

### 5. Provider capabilities are implicit

Priority: medium. Principles: open/closed, interface segregation and substitution.

`application/ports/research.py:29` describes provider identity, support and
collection. `application/research/planning.py:31` and line 77 onwards also discover
spatial, temporal, language and planned-query capabilities with `getattr`.
`application/research/pacing.py` and `source_admission.py` forward those implicit
members. Adding a capability can require coordinated changes to multiple wrappers.

Introduce typed immutable capability metadata and small optional behaviour ports
where justified. Keep conservative defaults for legacy/unknown capabilities.
Test that pacing and source-admission wrappers preserve relevant metadata and
behaviour. Existing wrapper tests already cover important cases; this is not a
claim that substitution currently has no test coverage.

### 6. Frontend boundaries and form contracts have widened

Priority: medium. Principles: single responsibility, interface segregation and
dependency inversion.

Four direct cross-feature imports conflict with the project convention:

- `frontend/src/features/direction/PlanPage.tsx:12` imports tracker presentation.
- `frontend/src/features/globe/CyberFilterPanel.tsx:14` imports cyber presentation.
- `frontend/src/features/reports/ReportPage.tsx:19` imports research scope policy.
- `frontend/src/features/reports/ReportPageFooter.tsx:4` imports its type.

Move these shared concerns to focused shared components or library modules, then
enforce feature boundaries with a resolver-aware lint/check rule covering relative
paths, aliases and type imports. Include failing fixtures for the check.

`ResearchForm.tsx:69` combines state, focus transitions, scope decisions and
submission with rendering. `useScheduleForm.ts:149`, line 174 and line 224 combine
normalisation, validation and request construction. `ScheduleFocus.tsx:10` accepts
the whole schedule form state. Extract pure policy/transition/request functions,
keep a small coordinating hook and provide narrower props and intention-based
callbacks. No new form framework or global store is needed.

### 7. Map extension requires repeated central edits

Priority: low. Principles: open/closed and interface segregation.

`features/globe/useGlobeScene.ts:12` names each catalogue's layer array, with
parallel render/dependency wiring later in the file. Prefer an ordered collection
of layer groups while retaining explicit top-level React hooks. Do not introduce
a dynamic hook registry. Extract infrastructure filtering and record presentation
from `InfrastructurePanel.tsx` when working on that feature.

`lib/map/MapEngine.ts:62` permits any object as a data layer, while
`MapLibreEngine.ts:249` casts it to a deck.gl layer. Make the payload contract honest
or parameterise it. This is a contract weakness, not a demonstrated runtime fault.

Backend paths above are relative to `backend/src/ase`; frontend paths without a
prefix are relative to `frontend/src`. Line references describe the reviewed
commit and may move during remediation.

## Delivery plan

Each row is a separate reviewable change or small series. Preserve public APIs,
database schema, source controls and saved-report behaviour unless a separately
reviewed requirement makes a change necessary. Rows 1 and 2 address behaviour;
later rows primarily reduce maintenance risk.

| Order | Deliverable | Acceptance criteria |
| --- | --- | --- |
| 1 | Model adapter exhaustion contract | Regression first; all supported explicit exhaustion signals produce the non-retryable outcome, draft generation performs one call, usage remains validated, partial content stays private, transient/validation retries still work. |
| 2 | Lifecycle ownership and factory separation | Inject failure at each startup stage and during cleanup; all previously owned resources close, later closes still run, original failures remain observable, importing the reusable factory does not instantiate the app. Normal startup/shutdown tests pass. |
| 3 | Frontend feature-boundary repair and enforcement | All four imports relocated without duplication; resolver-aware CI check rejects cross-feature imports, including type imports. Relevant page tests, typecheck, lint and build pass. |
| 4 | Thin research-brief API, then adjacent routes | Use cases are testable without FastAPI/SQLAlchemy; schemas accept result DTOs. Scope, revision-conflict, revoked-session, pagination and release tests pass. Add API-to-persistence import restriction with explicit, shrinking exceptions for remaining legacy cases. |
| 5 | Subscription and report workflow boundaries | Container wires services rather than executing admission policy. Preserve idempotency, lock order, lease fencing, budget reservations, cancellation and rechecks. Run relevant SQLite and PostgreSQL concurrency suites and report continuation tests. |
| 6 | Typed provider capabilities | New capability metadata needs no duplicated wrapper forwarding logic; wrapper matrix preserves area restrictions, language, planned-query support, registry routing, cancellation, disable controls and budgets. |
| 7 | Form and map simplification | Pure form transitions and payload builders have behavioural tests; small consumers accept narrow props. Layer ordering, renderer recovery, picking, selection and access invalidation remain covered. |

Do not measure completion by reducing constructor counts or splitting every file
above 350 lines. Review responsibilities and consumer needs. Do not split every
repository into per-method protocols, introduce microservices, or replace the
existing DI approach. File-size targets remain a useful warning, not the design.

For each implementation change, run focused regressions first, then the existing
lint/type/build/architecture checks and relevant CI suites. Keep existing coverage
gates. Security-sensitive extractions must preserve authorisation timing and
transaction boundaries, not just response shapes. Reassess the ratings after
implementation based on reduced coupling and passing behaviour contracts.

## Verification for this review

- `uv run lint-imports`: passed both contracts; 1,415 analysed files and 10,543
  dependencies.
- `uv run mypy src`: passed for 1,330 backend source files.
- `pnpm typecheck`: passed both frontend TypeScript projects.
- `python scripts/check_file_length.py`: passed, with 26 target-length warnings
  across production and test files; none exceeded the 400-line limit.
- Static production inventory: 1,330 backend Python files and 942 frontend
  TypeScript/TSX files. Excludes frontend tests/test helpers, generated declarations
  and vendored EvilEye. Thirteen backend and three frontend production files
  exceed 350 lines. These counts are context, not quality measurements.
- Offline parser checks confirmed the three-provider exception-class mismatch.
- Focused backend baseline: 41 tests passed in 35.94 seconds using
  `.venv/Scripts/python.exe -m pytest tests/test_report_budget_exhaustion.py tests/test_operator_task_production.py tests/test_candidate_registry_limits.py tests/test_research_challenge_collection.py --no-cov -q`.
  These existing tests do not assert cross-adapter exhaustion equivalence.

Full test coverage was not remeasured for this assessment. Existing historical CI
results do not prove all proposed contract requirements. No live model requests,
production changes, dependency updates or active security scan were performed.

# KAN-232: maintainability inventory and source limits

The inventory at `47a76fa118e12640aaa8e36c1e9ba1cdc70e4ebc` found 17 handwritten
Python/TypeScript files over the 350-line target, none over 400. Two stylesheets
were also over target, including the 636-line report reader. The complete
[inventory and policy](../MAINTAINABILITY.md) records every entry, its decision
and the boundaries to reassess on future changes.

## Changes

- Extend the existing checker to CSS, repository scripts/tests, frontend tooling
  and executable frontend configuration. Keep warnings above 350 and failure
  above 400, including physical comments and blank lines. Dependencies and
  existing generated/vendor exclusions remain outside its source inventory.
- Move schedule row conversion into `schedule_mapping.py` (133 lines). The
  repository/store module is 249 lines; existing `_from_row` consumers retain
  their compatibility export. Transaction and authorisation code is unchanged.
- Divide report-reader layout, evidence and media styles into coherent files.
  Keep motion, responsive and print overrides last in `reportReader.css`.
  Divide assistant panel/saved-chat styles from its composer in the same manner.
  CSS files now range from 72 to 256 lines.
- Record 16 specific target exceptions, all below the hard limit. The warnings
  remain visible; these are not exclusions or permission to exceed 400.

The primary checkout's instructions and shared workflow were read without
modification. All edits used the isolated `codex/KAN-232-maintainability`
worktree. File reservations were checked with the coordinator; deployment,
active feature work, workflow configuration and generated API remain with their
owners. No migration, dependency or provider behaviour changes are required.

## Validation

- The checker regression ran red first: a 401-line CSS file and five tooling
  locations escaped the old gate. The five CLI test methods now pass, covering
  those paths, 350/351/400/401 boundaries, CRLF/no final newline, declarations,
  vendor source and dependency exclusions.
- Before extraction, 69 focused schedule/research/outcome/change/monthly and
  subscription-publication tests passed. The first post-change run also passed
  all 69 cases, but inherited whole-application coverage settings and failed the
  90% gate at 41.10%. That was not a complete-suite coverage run. The final
  explicitly scoped run adds existing authority, archival, fair-queue and worker
  integration cases: all 88 pass, initially covering 87.39% of the two affected
  modules. Five added real-SQLite cases cover linked-plan removal/owner changes,
  a failure without a report, and stale saves after removal/archive. Those pass,
  bringing combined statement/branch coverage to **94.14%** across 93 cases,
  with the 90% gate retained. Mapping coverage is 100%; the repository/store is
  93%. This is focused coverage, not whole-application coverage.
- AST comparison confirmed both moved mapping bodies and every remaining
  repository/store/projection body are unchanged. Recursive CSS import expansion
  reproduces every original nonblank line in exactly the same order.
- Ruff check/format pass for changed Python source and tooling, using each
  directory's applicable configuration. Initial backend-policy lint over root
  CLI/test files reported CLI printing and the controlled subprocess fixture;
  the corrected root tooling invocation passes. The new test's formatting was
  corrected before the final check.
- Mypy passes across 1,613 source files. Its first pass caught the conversion
  alias needing an explicit export for two existing consumers; `__all__` now
  preserves that contract, and both focused and complete rechecks pass.
- All three import-linter contracts pass. Bandit passes for the changed backend
  modules and checker. The expanded file-length gate and `git diff --check` pass.
- Prettier passes for all seven changed/new CSS files. A private frozen/offline
  frontend install used Node 24.19.0. `pnpm build` passes, including application
  TypeScript checking. The bundle gate passes: initial JavaScript is 204,614
  gzip bytes against 245,760; additional globe JavaScript is 808,146 against
  870,400. Vite still prints its advisory warning about individual large chunks;
  no size threshold was changed.

Independent source review by the coordinator found no actionable issues in the
mapping, CSS order, checker or exception rationale. A final review of the added
SQLite adapter regressions also found no actionable issues. No browser/Vitest runtime,
full application suite, production services, live providers or shared database
were used. Backend tests clear shared `ASE_*DATABASE_URL`, `ASE_*TEST_URL` and
`ASE_*POSTGRES_URL` settings, including the rotation test URL.

## Integration

Re-run the inventory after combining branches. In particular, preserve KAN-221
subscription version/outcome changes when reconciling the extracted mapping,
and review any KAN-165 deployment-script growth. The combined OpenAPI contract
remains the coordinator's responsibility. This snapshot's passing check is not
evidence that the later combined branch has the same warning list.

The final coverage combines the 88-case run with the five new cases using
`--cov-append`; production source was unchanged between those runs. To reproduce
the combined group in one invocation from `backend`:

```powershell
uv run --frozen --offline pytest -o addopts=--strict-markers `
  tests/test_schedules.py tests/test_schedule_research.py `
  tests/test_schedule_outcomes.py tests/test_schedule_changes.py `
  tests/test_schedule_monthly.py tests/test_subscription_publication.py `
  tests/test_warning_scope_background.py tests/test_schedule_archive.py `
  tests/test_subscription_due_fairness.py tests/test_subscription_worker_integration.py `
  tests/test_schedule_mapping_integration.py `
  --cov=ase.adapters.persistence.schedules `
  --cov=ase.adapters.persistence.schedule_mapping --cov-fail-under=90
```

## Integrated migration startup follow-up

PR #187 head `e6712cd8` failed
[backend shard 1](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38008108154/job/114082066036)
because migration startup imported 204 project modules against its existing
limit of fewer than 200. The other 1,554 tests passed, with 43 skipped. The
no-container, no-application-factory and no-feed/LLM checks still passed.
The exact failure reproduced locally: one failure and one pass in 9.82 seconds.

The infrastructure CLI eagerly imported dataset adapters while registering
unrelated commands. Those adapters now load only when their selected command
runs. The shared contact default has the same value and was already loaded by
the Ukraine CLI. No migration, metadata, CLI option or output changed. A fresh
in-memory migration imports 196 project modules and none of the three deferred
infrastructure importer modules. The original startup budget is unchanged,
with explicit importer exclusions added to prevent regression.

All five infrastructure commands have dispatch regressions for default and
custom contacts, exact destination/layer arguments, returned counts and private
upstream failure details. Existing adapter tests now patch the adapter boundary.
The focused startup, dispatch, infrastructure and CLI/migration group passed
26 tests in 27.59 seconds. Ruff, formatting, scoped mypy, scoped Bandit and
`git diff --check` passed. Coverage and the whole backend suite were not rerun
for this focused repair. Tests used temporary or in-memory SQLite, cleared
shared database environment variables and contacted no external providers.
The coordinator independently reviewed the exact CLI/import/test diff without
findings. All touched source and test files remain below 350 lines.

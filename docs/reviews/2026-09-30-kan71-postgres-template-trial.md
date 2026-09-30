# KAN-71: explicit ordinary-app PostgreSQL templates

The successful 2 GiB storage trial took 45.80 aggregate PostgreSQL runner-minutes,
including its coverage merger. The 30-minute criterion remains unmet. This change
adds a test-only `--template-postgres` experiment; it does not enable it in CI.

The option requires `--isolated-postgres`. A prerequisite fixture establishes a
fresh owned database URL before the ordinary default settings/app fixtures and
other function-scoped consumers. A worker builds its template with the existing
SQLAlchemy schema helper, disposes the template engine, then disables connections
to that template. Each eligible test receives a separate UUID-named copy and a
fresh application engine. No application, session, user, password hash or Python
fixture state is cached.

Eligibility uses the effective default fixture function identities. Custom app or
settings fixtures, explicit PostgreSQL/migration/race lanes and independently
constructed databases retain their existing paths. SQLite and the generic schema
helpers are unchanged. Metadata changes, DDL callbacks and SQLAlchemy observers
require the normal DDL path. Setup and teardown recheck both the engine's exact
owned URL and eligibility. Application disposal now runs even when schema setup
or teardown fails.

Database names must belong to the creating worker's exact allocation/creation
registries; releasing a test also requires its active lease identity. Query-string
connection overrides are rejected before service DDL. DDL acknowledgement and
ownership bookkeeping complete before cancellation propagates. Failed drops keep
their ownership record for session cleanup. Cleanup never forces disconnections,
terminates another worker, or drops the service database. Environment restoration
runs even if cleanup fails.

## Evidence

The implementation was checked in an isolated worktree and virtual environment.
Real PostgreSQL checks used a new private loopback service with the same pinned
PostGIS 16.4 image as CI, 2 GiB tmpfs, two database CPU cores and a 2 GiB memory
limit. `fsync`, `synchronous_commit` and `full_page_writes` were observed ON. Each
pytest subprocess finished with zero remaining owned worker/template databases;
the container and its volumes were then removed.

- 41 focused guard, lifecycle, existing isolation and schema-helper tests passed
  in 2.45 seconds. These cover exact fixture overrides, ordinary `db` eligibility,
  special-lane exclusion, metadata/column mutation, DDL and named/once-wrapped pool
  listeners, foreign-engine refusal before and after fallback, cancellation,
  retained failed-drop ownership and URL restoration on test/cleanup failure.
- Four real PostgreSQL behaviour tests passed in 10.95 seconds. They exercise
  template sealing, independent rows/sequences, real commit/rollback visibility,
  late listener fallback, live-connection drop refusal and app setup-failure
  disposal.
- 19 opt-in correctness cases passed in 18.62 seconds: 14 cloned cases and five
  ineligible cases. The latter include the existing custom `test_events_api` app
  and WSDOT/OpenAlex settings overrides. No schema-admission fallback occurred in
  that sample. The clone count is admission, not a claim that later observers can
  never cause normal DDL.
- Changed-file Ruff, Ruff formatting and `git diff --check` passed. All changed
  Python modules remain below 350 lines. No production source or dependency was
  changed; no full suite, coverage measurement or CI trial was run for this flag.

The earlier scratch comparison also checked all 79 application tables against
Alembic and the complete catalogue: 779 columns, 313 constraints, 229 index
definitions and 13 sequences. It exercised server defaults, foreign-key and CHECK
failures, independent rows and sequence reset. Its one warm-up plus three measured
pairs showed a local 1.354-second current reset cycle versus a 0.223-second clone
cycle, including app construction and teardown, with 0.791 seconds to build the
template once. That result justified this narrowly scoped fixture trial.

## Representative application timing

After separate two-case warm-ups of both paths, the same 12 existing user/admin,
login, profile and password-change cases were run twice per variant in alternating
pair order. All 48 measured case executions passed. Whole pytest subprocess times
include imports, collection, fixture work, application tests and cleanup:

| Pair | Current isolated PostgreSQL | Template option |
| --- | ---: | ---: |
| 1, current then template | 27.850 s | 14.746 s |
| 2, template then current | 28.329 s | 15.012 s |

The median reduction is approximately 47.0% on this Windows/Docker Desktop host.
These are two serial local samples without coverage. They do not establish Linux
CI throughput, multi-worker behaviour, a variance estimate or the 30-minute
aggregate target. A bounded CI parallel-lane trial is still required, retaining
the selected cases, serial lanes, coverage, worker count, 2 GiB storage and all
durability settings.

Three independent read-only reviewers inspected ownership/security, fixture
architecture and lifecycle/quality. Review found and the implementation repaired
a teardown ownership-check short circuit and misclassification of wrapped pool
listeners; focused regressions protect both. Reviewers reported no remaining
actionable inspection findings. These reviews are not a claim of a scanner run.

The event guard intentionally recognises only the pinned SQLAlchemy factory's
built-in pool callbacks. An upstream implementation change may cause conservative
fallback and must be checked alongside dependency updates. Module/session-scoped
custom database fixtures, arbitrary SQLAlchemy extensions, runtime coverage and
full parallel-suite equivalence remain outside the local timing claim. Failure
of the service itself can prevent cleanup; errors are reported and never trigger
broader destructive cleanup.

## CI integration checkpoint

The shard runner exposes the explicit option only with `--postgres-mode parallel`;
normal and serial invocations reject it before starting pytest. All 14 runner
regressions pass. Ruff and formatting pass for all 11 changed Python files, and
Actionlint 1.7.12 validates the workflow. The parallel PostgreSQL command enables
the option for one bounded CI trial. Workers, selection, coverage, storage,
durability settings and the serial command remain unchanged. Full Linux CI,
multi-worker eligibility counts and aggregate cost are pending at this checkpoint.

### First CI SQLite compatibility repair

Run `36712872629` at `83bbc802` exposed two setup errors in SQLite shard 5:
the new opt-in tests requested the session-scoped template worker before their
function-scoped option gate could skip. The shard otherwise passed 1,251 cases
and skipped one. The test signatures now retrieve the existing worker inside
the test, after the option gate and app setup. No application fixture, selection
or deadline changes. Before the repair, both errors reproduced locally; after it,
both tests skip in 0.18 seconds without service URLs and pass against a fresh
owned PostgreSQL service in 2.03 seconds. That run cloned both cases, retained all
three durability flags and left zero owned databases. Ruff/format and whitespace
checks pass. The running PostgreSQL CI jobs were retained for honest timing and
census evidence; a new complete CI run is required after publishing this repair.

## First CI trial and focused repairs

Run 36712872629 at `83bbc802569c982a71bd5c17aae2afb03463de18` failed:
SQLite encountered eager session-fixture setup in the two opt-in tests, and one
PostgreSQL shard encountered an unhashable mock attribute during classification
and a non-zero template activity snapshot. The failed shard skipped its serial
lane and coverage upload. Its four PostgreSQL jobs plus failed merger consumed
39.6167 runner-minutes; this incomplete run is excluded from performance acceptance.
The complete target and census still require a successful subsequent CI run.

The opt-in tests now retrieve the worker only after their option gate and app
setup. Classification constrains dynamic `__name__` and `__module__` attributes
to strings while retaining literal factory names and alias/closure traversal.
Focused regressions reproduced the invalid mock attributes before this repair.

The redundant `pg_stat_activity` precheck was removed. PostgreSQL 16.4's
[database-copy implementation](https://github.com/postgres/postgres/blob/REL_16_4/src/backend/commands/dbcommands.c#L1225-L1238)
uses its locked source check, and
[CountOtherDBBackends](https://github.com/postgres/postgres/blob/REL_16_4/src/backend/storage/ipc/procarray.c#L3440-L3523)
waits up to five seconds for ordinary backends to exit. PostgreSQL itself also
handles conflicting autovacuum workers. The fixture retains its ten-second
command timeout, exact owned source validation and sealed template. It issues
no termination, FORCE or unseal command. The original CI log cannot identify
which backend produced its non-zero activity observation.

Follow-up validation on the same pinned private PostgreSQL 16 service, 2 GiB
tmpfs and all three durability settings on:

- 48 classification, lifecycle, ownership and existing isolation/helper tests
  passed. Native CREATE refusal preserves ownership and closes the service
  connection; the existing cancellation acknowledgement test still passes.
- Seven real PostgreSQL cases passed, including eight consecutive empty clones
  and native transient/persistent client tests. Those tests retain a client
  before sealing, observe CREATE running, then either release it or verify
  native refusal while the original client remains usable.
- 23 cases passed with two xdist workers across camera catalogue, password change
  and opt-in fixture tests: 22 clones, zero admission fallback, one ineligible.
  Both actual PostgreSQL CI error paths ran successfully.
- The default opt-in-test invocation without service URLs reports two skips.
  Owned database census was zero after each PostgreSQL subprocess, and the
  private service and volumes were removed. Ruff and whitespace checks passed.

These focused results do not replace full CI, coverage or aggregate timing.

## Repaired full CI checkpoint

Run `36715508656` at `a0e1f6eb919a976e7d29d7988aceedb0a4f191a0`
passed all 30 jobs. PostgreSQL executed 2,392 unique cases: 2,114 parallel and
278 serial. All 2,367 baseline cases remain, with 25 additions, no duplicates
and no lane changes. The template path admitted 1,751 clones, with zero schema
admission fallbacks and 363 ineligible cases using normal schema creation.

The four PostgreSQL jobs took 631, 621, 630 and 679 seconds; their merger took
32 seconds. Aggregate cost was 2,593 seconds (43.2167 runner-minutes), so the
30-minute acceptance target remains unmet. Parallel steps consumed 1,829 seconds,
serial steps 584 seconds, and other job work 148 seconds. This is a complete
passing checkpoint, not completion of the performance acceptance criteria.

All 84 capacity samples succeeded. Peak storage was 310.336 MiB of 2 GiB,
minimum free space was 1,737.664 MiB, and WAL peaked at 80 MiB. All four jobs
retained the three enabled durability settings. Supplemental PostgreSQL coverage
was 74.9518 percent; the separate global backend coverage gate passed unchanged.
Frontend coverage, security checks, Semgrep and image builds also passed.
Raw logs, executed node lists, settings, capacity and coverage artefacts are
retained outside Git in the coordinator's `ci-36715508656` evidence directory.

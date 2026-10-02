# CI and test health batch: KAN-69 to KAN-76

Original base: `69696286`. Branch: `codex/KAN-69-ci-test-batch`.
Stacked PR base: `codex/KAN-41-runtime-observability` at `3e874208`.
The runtime and architecture dependency branches merged without conflicts.
This record distinguishes implementation and measured local evidence from acceptance
criteria that require completed GitHub runs. No production deployment is authorised.

## Changes and remaining acceptance evidence

| Ticket | Implemented | Evidence still required |
| --- | --- | --- |
| KAN-69 | Four Vitest blob shards, merged coverage, separate lint/type/build checks, reusable workflow and preserved required `frontend` check. Failure reports are retained. Two complete Linux frontend runs passed, with every shard below six minutes including setup. | Final combined-tree run and five comparable before/after runs. |
| KAN-70 | Per-job idle progress budgets observe committed stage/status/payload changes, ignore heartbeat-only changes, cancel and join unfinished tasks, and keep an overall cap. Shared report workers receive the slow marker. Backend shards print the 20 slowest tests. | Twenty consecutive main CI runs without the reported timeout. |
| KAN-71 | Four PostgreSQL shards select persistence fixtures/helpers and explicit PostgreSQL, migration and race tests. Ordinary database tests use private worker databases; special database tests run serially. All four Linux shards and their merger passed. The 2,361 executed node IDs omit none of the 2,360 reviewed persistence cases. SQLite keeps the sole global 90% backend gate. | Five-run runner-minute comparison. |
| KAN-72 | Reviewed backend security and frontend auth modules have 95% line and branch gates. Added 84 backend boundary tests, MFA/session lifecycle tests and login feedback cases. Missing reviewed modules fail the checker. Fresh merged Linux backend and frontend reports pass all reviewed floors. | Final combined-tree confirmation. |
| KAN-73 | 88 existing pure test files moved into the Node project, including one already-skipped benchmark; DOM tests retain jsdom and MSW. | Same-machine before/after timing, at least 70 seconds saved and full coverage difference within 0.05 percentage points. |
| KAN-74 | Behavioural coverage across maps, research, auth, assistant and report controls. Narrow chart validation and map seam continuity fixes retain edge-case behaviour. Fresh merged Linux coverage reaches 92.16% branches with every file of at least 20 branches at 70% or above. The checker enforces these floors and prints the ten worst files. The subsequent Linux run passed the strict gates. | Final combined-tree confirmation. |
| KAN-75 | `build:ci` avoids duplicate TypeScript work after the explicit typecheck. Docker defaults retain the full build; CI opts into the lighter command. API/web images build and scan in parallel with separate GHA caches and a fail-closed `images` aggregator. Security uses the pnpm cache. Dependabot major holds include review dates. Undici and brace-expansion updated within existing dependency ranges. Cached image jobs measured 69/44 seconds. | One unchanged-lockfile image path completed in 69 seconds including its aggregator. Repeatability and four weekly Dependabot observations remain outstanding. |
| KAN-76 | MSW handlers split into focused admin/response modules. Photo-geolocation lifecycle tests split from the interaction suite. All touched split files stay below 350 lines. Full Linux frontend CI passed after extraction. | Final combined-tree confirmation. |

## Measured checks

- Complete run `36696097087` passed at `cccfa79f`, including all 2,363 selected
  PostgreSQL cases and the strict coverage/security floors. PostgreSQL jobs used
  53.75 runner-minutes (excluding the merger), compared with 62.10 in the earlier
  successful run. The 13.4% reduction does not meet KAN-71's 30-minute target.
  Parallel test steps used 41.73 minutes, serial steps 9.40 and other job steps
  2.62. Collection improvements preserve the selected cases and all isolation.
- The [CI timing census](../evidence/2026-09-30-KAN-69-75-ci-timings.md) records
  five operational frontend observations before and after sharding. All twenty
  after shards finished within six minutes, at a maximum of 263 seconds.
  Different source, workflow and dependency snapshots prevent interpreting these
  observations as same-source controlled pairs. The latest cached image path
  completed in 69 seconds including its aggregator, with unchanged lockfiles;
  elapsed Dependabot observations remain separate acceptance.

- GitHub run `36662274115` on `ff3fb53d` passed all frontend shards, static/build
  checks and merged coverage. It covered 20,266/21,988 branches (92.1684%, displayed
  as 92.16%), 97.28% lines, 96.16% statements and 94.30% functions. No file with at
  least 20 branches is below 70%; the auth 95% floors also pass. An independent
  LCOV scan matches the branch numerator and denominator exactly. The workflow
  now enforces the measured 92% global and 70% per-file floors without changing
  the original four Vitest thresholds or excluding production code.
- The same run passed all eight SQLite shards, all four PostgreSQL shards and both
  backend mergers. Its PostgreSQL artefacts contain 2,361 unique node IDs: none of
  the 2,360 reviewed cases is omitted, and the additional case is the new SQLite
  checkpoint-isolation regression. Run `36663903807` subsequently passed all
  frontend checks including the enabled 92%/70% branch and 95% auth gates.
- GitHub run `36659162698` completed all four frontend shards, static/build checks
  and the merged 90% coverage gate. Merged branches were 20,016/21,988 (91.03%).
  This establishes a consistent Linux baseline for the remaining 92% target.
- GitHub run `36661309612` completed all eight SQLite shards and their merger:
  combined coverage was 94%, and every reviewed backend security floor passed.
  Its frontend also passed all four shards, checks and merger, with 20,111/21,988
  branches (91.46%). The frontend auth checker passes this fresh merged report.
- Frontend shard durations including setup were 148, 263, 205 and 237 seconds in
  run `36659162698`, then 215, 234, 175 and 182 seconds in `36661309612`.
  An independent LCOV branch scan agrees exactly with both JSON summary totals.
- The first image job completed in 518 seconds; the next completed in 155 seconds.
  In the second, API/web build steps took 38/47 seconds, with both smoke and Trivy
  checks passing. The 85-second sum of build steps is not the whole-job target.
  The subsequent two-image matrix removes sequential builds/scans while preserving
  the required `images` result and every scan. Its first API/web jobs took 89/69
  seconds, with 93 seconds from their first start to the aggregator finishing.
  The next cached jobs took 69/44 seconds, but the aggregator waited 55 seconds
  to start, making end-to-end elapsed time 128 seconds. Individual execution times
  meet the 90-second target; overall completion including scheduling does not yet.
- Frontend authentication: 67 tests across 12 files passed in 53.53 seconds.
  Every reviewed auth module passes 95% lines and branches. Direct routed feedback
  tests exercise rejected sign-in and rate limiting without booting the full shell;
  full-page successful sign-in and keyboard interaction tests remain.
- The SQLite schedule-edition CI failure was reproduced as a dirty checkpoint read
  and lost worker write: the old single-connection fixture returned `(1, 0)` instead
  of `(0, 1)`. Report-worker modules now use private file-backed SQLite unless an
  explicit PostgreSQL URL is supplied. The regression, schedule and wait tests
  passed (seven cases), followed by 43 fixture/marker/report API cases.
- The newly enabled PostgreSQL serial lane exposed stale fixtures. The teams
  migration test now verifies the three seeded allowances before testing uniqueness;
  FIRMS races request their real feed catalogue and hook the extracted poller;
  the legacy subscription migration gets a database satisfying its existing
  disposable-name guard. Both migration modules passed (three cases), followed by
  all ten real PostgreSQL FIRMS concurrency cases. Ruff and Actionlint passed.
- Added research control/declaration coverage: 46 focused tests, all four target
  modules at 100% branches (136/136). Report controls and assistant positioning:
  62 focused tests, 121/122 target branches. Research/assistant lifecycle and
  original-asset boundaries: 181 focused tests, 467/475 target branches. Radar
  and Ukraine headline figures: 12 focused tests, 51/51 target branches. These
  focused reports supplement the baseline; they are not a new full-suite result.
- Map/input lifecycle tests passed 82 cases, covering 305/311 target branches.
  An LCOV key comparison found 60 newly covered branches and no lost covered
  branches. Geometry tests passed 54 cases, covering all 129 topology/local-GeoJSON
  branches. They reproduced an existing 355-degree rendered segment after an
  equivalent +180/-180 endpoint. Continuing from the displayed endpoint fixes
  both seam directions without mutating the original coordinates.
- Script unit suite: 77 tests, 74 passed and three existing platform skips.
  The coverage-checker suite subsequently passed all seven tests after adding
  an omitted-module regression case, including diagnostic mode.
- Backend progress, isolation and shard-helper focused checks: passed. The progress
  helper covers idle starvation, continuing checkpoints, overall expiry, worker
  failure and a stalled initial snapshot.
- Real disposable PostgreSQL: five report-job API tests passed with two workers.
  Both worker databases were observed and then absent after teardown. The fixture
  restricts creation to loopback PostgreSQL and drops only its generated identifier.
- Economy briefing: five tests passed without coverage in about 62 seconds. A later
  coverage run completed all five economy and five progress tests before being
  interrupted to release shared CPU; its remaining tests/report are not claimed.
- Node project: 87 files and 652 tests passed; one existing benchmark file/test was
  skipped. Wall time was 63.81 seconds with two workers.
- Photo-geolocation focused suites: 22 tests passed after the split.
- Map layers: seven tests passed, measuring 100% branches (67/67), lines, statements
  and functions for `evidenceMapLayers.ts`.
- Terrain chart: nine tests passed, measuring 86.95% branches (40/46) and 100% lines,
  statements and functions. The null guard preserves handling of NaN and infinity.
- Saved-chat lifecycle suite: 16 tests passed in 6.74 seconds, measuring 83.75%
  branches by itself; existing integration coverage is additional.
- Backend security floor: the exact-base successful CI SQLite shard artefacts from
  run `36508802767`, combined with measured new-test arcs, pass every reviewed
  module at 95% lines and branches. Source paths were remapped between worktrees;
  production auth/validation source was unchanged. This is not a fresh full run.
  Removing the new auth-test measurements by checking the prior CI/validation
  report returns exit 1 and names report authorisation (85.42% lines, 68.18%
  branches), demonstrating that the higher gate rejects the earlier gap.
- Lockfile audit after updating Undici 7.29.0 to 7.30.0: zero vulnerabilities.
  Before the update, the audit reported two high, five moderate and three low.
  The package source and integrity were verified against npm metadata and the
  [official signed release](https://github.com/nodejs/undici/releases/tag/v7.30.0).
- A later advisory update made run `36663903807` fail its frontend audit, with six
  high and three moderate brace-expansion findings. Updating only its existing
  transitive resolutions to 1.1.21, 2.1.7 and 5.0.12 restores zero known audit
  vulnerabilities. Package repositories and integrity hashes match official npm
  metadata. These versions fix the upstream
  [nested expansion](https://github.com/advisories/GHSA-qhr7-859c-m2p7) and
  [comma parsing](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p) recursion
  advisories. Frozen installation, unchanged generated API types, five focused
  Vitest cases, targeted ESLint, production build and bundle budget checks passed.
- Frontend TypeScript and changed-file Prettier checks passed. Backend Ruff lint
  and formatting passed across all 25 changed or newly added test/helper files.
  Whitespace and file-length checks passed. Actionlint with ShellCheck passed for
  both changed workflows. The installed Vitest 5 reporter source confirms the
  `.vitest/blob` directory and shard filenames used by the merger.
- Changed-file ESLint passed after correcting an unnecessary optional chain
  after narrowing and explicitly awaiting the cancelled test response.
- Selection review added nested-code and captured-factory traversal, plus a
  conservative file fallback for actual database constructor calls. All 18
  progress/isolation/selection tests passed. The census selected 2,360 of 10,086
  cases across 438 files. No file containing a direct, nested or method database
  constructor was absent from the selection. This is selection evidence, not
  the execution evidence; the later Linux run and artefact census above provide it.
- Installed Vitest 5.0.1 project resolution explicitly inherits the declaring
  config for inline projects by default. Root mock-reset and timeout settings
  therefore remain applied to both projects.

## Interrupted frontend diagnostic run

The Windows full coverage run progressed for about 26 minutes. It reported one
BriefWorkspace failure and two LoginPage failures before cancellation. A subsequent
pnpm command automatically synchronised the updated lockfile, so the interrupted
run spans two dependency installations and cannot establish a final baseline.
Raw coverage fragments and logs remain outside tracked files as diagnostics.
The exact-base successful GitHub run has no frontend coverage artefact.

The pending-login test had asserted the HTTP handler count immediately after the
busy UI appeared. It now waits for the first request to reach MSW and releases its
pending response in a finally block, avoiding leakage if an assertion fails.
The consistent Linux frontend run subsequently passed BriefWorkspace and all
LoginPage cases. The interrupted Windows result is retained only as diagnostic
history, not evidence of a current Linux regression.

## Security and compatibility

Required `backend`, `backend-postgres` and `frontend` check identities remain.
The global SQLite backend and frontend 90% gates remain unchanged. KAN-71
explicitly removes the duplicate PostgreSQL coverage percentage gate: every
selected PostgreSQL test must still pass, and combined PostgreSQL coverage is
published as an artefact. Partial shards do not apply whole-application coverage
thresholds; the SQLite and frontend mergers enforce them. No changed coverage exclusion hides
production code. Frontend auth enforces its measured 95% floor; the measured
92% global branch and 70% per-file branch floors are also enforced.
Action versions are pinned to verified upstream release commits. Image jobs load
locally for existing Trivy/smoke checks and do not push images. No deployment or
SBOM workflow is changed in this batch.

## Main integration checkpoint, 1 October 2026

Merged runtime parent `6eeca4cf41134fea9070b22ab589f3ae44c7da99`, which includes
main `9ae40e3d`, into this batch without rewriting history. Main's login focus
and `aria-disabled` assertions remain alongside the deterministic request wait
and guaranteed response release. Its page-title, error-message and readability
assertions are preserved exactly under their `.unit.test.ts` names. The team
fixture retains both the router/path wrapper and the pure-data re-exports.
Frozen private installs retain PyJWT 2.15.1, urllib3 2.8.0 and axe-core 4.13.0.

- Focused frontend: 203 tests passed across 25 files, including auth, teams,
  terrain and the changed/new Node suites. Both TypeScript configurations,
  targeted ESLint/Prettier, Ruff and 21 shard/coverage-policy tests passed.
- Backend fixture/guard regressions: 58 passed. A private PostgreSQL service
  passed seven clone/ownership/listener/native-lock tests and two ordinary-app
  template cases. Fsync, synchronous commit and full-page writes stayed on;
  no owned child databases remained after the checks.
- The current metadata contains 85 tables. Its fingerprint remained
  `5304c8f8b987365689e35e96b806f80d6c47062d2bb05c386ed757194aba812c`
  before and after collection. SQLAlchemy remains pinned to 2.0.54.
- Collection found 10,391 cases in 927 files. The four PostgreSQL shards select
  2,248 parallel and 293 serial cases exactly once. Actual pytest marker
  collections match that partition, and all 2,363 previously selected case IDs
  remain selected. Existing untracked census evidence was preserved.
- Actionlint with ShellCheck passed after documenting its two narrow storage
  sampler false positives: indirect trap invocation and container-side variable
  expansion. The sampler's execution and cleanup are unchanged.

Full coverage and current-head CI remain pending at this integration checkpoint.
Main's successful run `36919106432` reports 90.47% frontend branches and uploaded
no frontend coverage artefact. Additional behaviour-test commits will follow;
the global 92%, eligible-file 70%, auth 95% and existing global 90% gates and all
coverage exclusions remain unchanged. Earlier timing and coverage measurements
do not establish acceptance on this expanded source tree.

### Integrated frontend coverage and compatibility repairs

The first complete Linux run used the exact tracked tree at `d7accf7b`, a fresh
frozen pnpm installation, Node 24.21.0, two workers and a container limited to
two CPUs and 6 GiB. All 5,403 tracked files matched their archived hashes before
and after execution. Raw V8 JSON, LCOV, coverage summary, test JSON and the Vitest
blob remain outside Git under `main-integration-20261001/frontend-d7accf7bcbc3`.

That run is diagnostic, not a passing suite: 4,280 cases passed, five failed and
one was skipped. Independent raw JSON and LCOV counts agree on 22,742 of 24,694
covered branches (92.09%). Authentication passed its 95% floor. The only eligible
module below 70% was `useLiveViewOpening.ts`, at 18 of 28 branches.

Both failing files contained assertions predating main's accessibility changes.
Four copy-button cases expected native `disabled`; the repaired tests retain
duplicate-submission and cancellation checks while asserting `aria-disabled`,
`aria-busy` and preserved focus. One figures case expected the old sparkline
name; it now asserts the complete accessible period, values and range. These
failures were reproduced before the test-only fixes. The corrected suites and
their form, button and figures consumers passed 20 and 10 tests respectively,
with scoped ESLint and Prettier passing. Production behaviour is unchanged.

Seven new live-view opening cases exercise real router/store behaviour around
rotation area cleanup, manual area preservation, dismiss/access/unmount
cancellation, late responses and repeated reads of the same ID. Together with
four existing round-trip cases, they pass with all 28 branches, 51 lines,
65 statements and 18 functions covered. The full current-head suite and gates
must still pass after these changes; these focused results do not relabel the
earlier failed run.

# CI and test health batch: KAN-69 to KAN-76

Original base: `69696286`. Branch: `codex/KAN-69-ci-test-batch`.
Stacked PR base: `codex/KAN-41-runtime-observability` at `3e874208`.
The runtime and architecture dependency branches merged without conflicts.
This record distinguishes implementation and measured local evidence from acceptance
criteria that require completed GitHub runs. No production deployment is authorised.

## Changes and remaining acceptance evidence

| Ticket | Implemented | Evidence still required |
| --- | --- | --- |
| KAN-69 | Four Vitest blob shards, merged coverage, separate lint/type/build checks, reusable workflow and preserved required `frontend` check. Failure reports are retained. The first complete Linux frontend run passed. | Final combined-tree run, shard timing review and five comparable before/after runs. |
| KAN-70 | Per-job idle progress budgets observe committed stage/status/payload changes, ignore heartbeat-only changes, cancel and join unfinished tasks, and keep an overall cap. Shared report workers receive the slow marker. Backend shards print the 20 slowest tests. | Twenty consecutive main CI runs without the reported timeout. |
| KAN-71 | Four PostgreSQL shards select persistence fixtures/helpers and explicit PostgreSQL, migration and race tests. Ordinary database tests use private worker databases; special database tests run serially. Selected node IDs and diagnostic coverage are retained. SQLite keeps the sole global 90% backend gate. | Complete Linux PostgreSQL regression run, node-ID census and five-run runner-minute comparison. |
| KAN-72 | Reviewed backend security and frontend auth modules have 95% line and branch gates. Added 84 backend boundary tests, MFA/session lifecycle tests and login feedback cases. Missing reviewed modules fail the checker. The 67-test frontend auth suite passes every reviewed floor. | Fresh full SQLite shard run and merged Linux confirmation of the frontend auth gate. |
| KAN-73 | 88 existing pure test files moved into the Node project, including one already-skipped benchmark; DOM tests retain jsdom and MSW. | Same-machine before/after timing, at least 70 seconds saved and full coverage difference within 0.05 percentage points. |
| KAN-74 | Seven map-layer boundary tests, three terrain chart cases, and 16 saved-chat error/cancellation tests. The chart narrows validated heights once and removes unreachable fallbacks. The merged CI report prints ten worst files and remaining floor gaps. | Global branches at least 92%, and every file with at least 20 branches reaching 70%. This ticket is not complete. |
| KAN-75 | `build:ci` avoids duplicate TypeScript work after the explicit typecheck. Docker defaults retain the full build; CI opts into the lighter command. Pinned Buildx actions load test images with separate GHA caches. Security uses the pnpm cache. Dependabot major holds include review dates. Undici updated within the existing jsdom range. | Clean and cached image builds and live CI timing evidence. |
| KAN-76 | MSW handlers split into focused admin/response modules. Photo-geolocation lifecycle tests split from the interaction suite. All touched split files stay below 350 lines. Full Linux frontend CI passed after extraction. | Final combined-tree confirmation. |

## Measured checks

- GitHub run `36659162698` completed all four frontend shards, static/build checks
  and the merged 90% coverage gate. Merged branches were 20,016/21,988 (91.03%).
  This establishes a consistent Linux baseline for the remaining 92% target.
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
  evidence that all selected PostgreSQL tests have executed.
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
production code. Frontend auth now enforces its measured 95% floor; the 92% global
branch and 70% per-file branch floors remain report-only while gaps exist.
Action versions are pinned to verified upstream release commits. Image jobs load
locally for existing Trivy/smoke checks and do not push images. No deployment or
SBOM workflow is changed in this batch.

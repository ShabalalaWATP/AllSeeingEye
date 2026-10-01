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

### Passing full frontend validation

A second fresh frozen Linux run of `18ce82452e861ba2166261306065aa71419e0aff`
passed all 4,292 active cases across 793 files; one existing case/file remains
skipped. The same pinned Node image, two-worker limit and resource bounds were
used. All 5,405 tracked source hashes were unchanged after execution.

Raw V8 JSON and LCOV independently agree on 22,754 of 24,694 branches (92.14%).
Lines are 97.37%, statements 96.22% and functions 94.68%. The current source
inventory passed both policy scripts: authentication at 95%, global branches
at 92% and every eligible file at 70%. No threshold or exclusion changed.
Both TypeScript configurations and scoped lint/format checks also passed.
Raw reports and the frozen-input manifest are retained outside Git under
`main-integration-20261001/frontend-18ce82452e86`. This validates frontend
correctness and coverage only, not the separate timing targets or GitHub CI.

Evidence directory: `C:/Users/alexo/.codex/worktrees/kan69-ci-tests/main-integration-20261001/frontend-18ce82452e86`.
The earlier failed diagnostic is retained separately in sibling directory
`frontend-d7accf7bcbc3`.

- `manifest.json`, `tracked-sha256.json` and `source.tar`: exact frozen Git inputs.
- `installation.json` and `install.log`: fresh private frozen install, Node
  24.21.0 and pnpm 11.25.0, with container resource settings.
- `run-result.json` and `coverage.log`: command, UTC timestamps, exit code zero,
  complete test outcome and post-run source verification.
- `coverage/coverage-final.json`, `coverage/coverage-summary.json` and
  `coverage/lcov.info`: raw branch maps and independent count reconciliation.
- `tests.json` and `blob.json`: complete Vitest case/file results and mergeable report.
- `verified-summary.json`, `frontend-auth.log` and `frontend-branches.log`:
  independently counted 4,292 passing cases, one existing skip and both policy passes.

Pinned image:
`node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1`.
The owned container was stopped and removed after the artefacts were copied.
No unrelated resources were changed. PR91 remains frozen at the tested
`18ce82452e861ba2166261306065aa71419e0aff`; this note is held outside Git for the
final integration documentation and does not restart the current CI stack.

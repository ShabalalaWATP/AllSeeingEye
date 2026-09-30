# KAN-73 worker-pool screening, 30 September 2026

The 70-second whole-suite saving remains unmet. The controlled comparison on
`c76d944087df1f45396b0f3104478e9a06cab55b` saved **63.8142947 seconds**:
905.0024985 seconds with all files using DOM setup, versus 841.1882038 seconds
with 113 unit files assigned to Node. Both phases passed 662 files and 3,644
tests, with one existing skipped file/test. All four coverage totals were
identical, including 20,266/21,988 branches (92.16%).

Two bounded follow-ups investigated worker startup overhead. Neither changes
the delivered configuration or completes the timing acceptance criterion.

## Reproducible inputs

- Complete source: the same `c76d9440` archive, containing 4,947 tracked files.
- Archive SHA-256:
  `8609259e6ad1663d9f0ff9b86dfc6167d3059f2dff2b8db82c120716c653a66a`.
- Node 24.21.0, pnpm 11.25.0 and Vitest 5.0.1 in the private two-CPU, 6 GiB
  Docker container. Image:
  `node:24-alpine@sha256:ebfe2f90462722a7a4de65e91990e97fe0d401c70e0e762c5b53302f905ec1c1`.
- Frozen source and installed lock SHA-256:
  `8e997ae0414e0f06f383c9f21ee024e873256f6305bb094afacd0f7034c9f78b`.
- Two workers, unchanged test cases, mock resets and coverage configuration.
- Before each measured arm: the same five infrastructure fixture cases,
  restoration of the captured empty Vite/Vitest cache roots, then ten seconds
  of cooldown. Cache-state SHA-256:
  `4586d769eff0c51b723397663430aa9dd3955c3648f44679054a19308a35f097`.

## Ordinary threads: compatible but insufficient gain

The candidate changed only the unit project's pool from the default `forks`
to `threads`. The DOM project retained forked processes and its original setup.

| Predetermined arm | Start, UTC | Wall seconds | Results |
| --- | --- | ---: | --- |
| Forks | 11:21:45.175008 | 31.1237436 | 112 files and 796 tests passed; one existing skipped file/test |
| Threads | 11:22:30.082290 | 29.6381911 | Identical cases and outcomes |

The **1.4855525-second** saving was below the approximately seven-second screen
needed to justify another complete comparison. The exploratory configuration
change was reverted. There was no repeated or selected favourable timing run.

Both arms retained the complete production coverage include set and 90% global
thresholds. They exited with the expected coverage-only failure because the
remaining UI tests were not selected. This was not a passing full coverage run.
Both recorded exactly the same 1,038 per-file summaries and covered LCOV
locations: 3,527 lines, 3,976 statements, 830 functions and 3,324 branches.
The complete source, configuration and installed-lock checks also passed.

A separate six-file, 12-test concurrency witness observed real fork/thread
overlap with a peak of two active files and pool IDs restricted to 1 and 2.
Resolved configuration preserved `isolate: true`, `restoreMocks: true` and
`clearMocks: true` for both projects. Fresh-global and between-test reset
assertions passed.

Installed Vitest's `dist/chunks/index.DzobfTyw.js` creates one `Pool` at line
11610 and caps its shared `activeTasks` at line 11428. Worker type is selected
per task at lines 11536–11540. Thus the two projects do not each acquire an
independent two-worker budget. Existing asynchronous worker teardown may
overlap startup; the measured limit concerns active test execution.

## VM pools: rejected for different isolation semantics

Vitest supports `vmForks` and `vmThreads`, but its configuration resolver sets
`isolate: false` for these pools (`index.DzobfTyw.js`, line 14508). It creates
a fresh VM context and module executor per file while reusing the host worker.
`dist/chunks/vm.W4G5WMTl.js` injects the host `process` into that context and
returns host native built-ins. Fresh VM globals therefore do not preserve the
existing per-file process boundary.

An eight-file, 16-test witness passed fresh-global, local-module-state and
mock-reset assertions. Four VM files reused two processes, with recorded PIDs
`110, 117, 110, 117`. It observed a peak of two active files, though the DOM and
VM portions did not overlap during this particular witness. Native filesystem
errors satisfied `instanceof Error` in all four DOM/forks files and failed that
check in all four VM contexts. This confirms a concrete semantic difference.

These boundaries agree with the official [pool documentation](https://vitest.dev/config/pool.html)
and [isolation documentation](https://vitest.dev/config/isolate.html). The
[VM memory documentation](https://vitest.dev/config/vmmemorylimit.html) also
describes retained contexts and worker recycling. The small witness does not
establish acceptable memory use for the real suite.

The coordinator rejected VM pools for delivery. The newly started forks
baseline was stopped before the timed VM arm. No complete VM performance,
coverage or memory result is claimed. No custom worker, polyfill, reset
weakening or repository configuration change was retained.

## Retained evidence

Local artefacts are outside the checkout, under
`C:/Users/alexo/.codex/worktrees/`:

- `kan73-paired-c76d9440/paired-result.json`: completed whole-suite pair,
  archive, configurations, logs, case identities and coverage.
- `kan73-node-expansion/pool-screening/screen-result.json`: completed threads
  screen, case/coverage comparison, concurrency witness and reproduction scripts.
- `kan73-node-expansion/vm-screening/concurrency-result.json`: VM witness,
  resolved settings, native-error observations and the interrupted screening
  log. The interrupted arm is diagnostic only.

The owned benchmark container was stopped after the work. No unrelated
container was changed. KAN-73 retains the measured **63.81-second** improvement,
with the **70-second** acceptance criterion explicitly outstanding.

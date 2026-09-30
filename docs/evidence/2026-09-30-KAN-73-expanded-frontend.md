# KAN-73 expanded Node project comparison

The second controlled whole-suite pair saved **63.8142947 seconds**, below the
70-second criterion. Both configurations passed exactly the same 3,644 cases
and produced identical raw coverage. This result does not complete KAN-73.

Frozen source: `c76d944087df1f45396b0f3104478e9a06cab55b`, including the 20
additional mechanical renames. There are 113 unit-project files. Both arms used
Node 24.21.0, pnpm 11.25.0, two workers, two CPUs and 6 GiB in one private Linux
container. The entire 4,947-file repository archive was used, with a frozen
installation. Only the unit environment, jsdom URL and setup file differed.

Before any tests, all three Vitest/Vite cache roots were captured as absent.
Each arm ran the same five-case warm-up, restored that identical empty state,
then waited ten seconds. The predetermined order was DOM followed by Node;
neither phase was retried. All source, configuration, installed lock and cache
hashes were verified after both phases.

| Measurement | DOM | Node |
| --- | ---: | ---: |
| Wall time, seconds | 905.0024985 | 841.1882038 |
| Passing files / cases | 662 / 3,644 | 662 / 3,644 |
| Existing skipped files / cases | 1 / 1 | 1 / 1 |
| Covered lines | 19,981 / 20,538 | 19,981 / 20,538 |
| Covered statements | 22,461 / 23,357 | 22,461 / 23,357 |
| Covered functions | 7,323 / 7,766 | 7,323 / 7,766 |
| Covered branches | 20,266 / 21,988 | 20,266 / 21,988 |

Case names, outcomes and counts match exactly. Coverage changed by zero
percentage points, satisfying the 0.05-point tolerance. The timing target was
missed by 6.1857053 seconds. The owned benchmark container was stopped after
validation; no test scope, isolation or coverage threshold was weakened.

[Machine-readable evidence](2026-09-30-KAN-73-expanded-paired-result.json)
records commands, timestamps, hashes and acceptance flags. Full logs, case
identities, LCOV, source archive, cache snapshots and phase scripts are retained
outside Git at `C:/Users/alexo/.codex/worktrees/kan73-paired-c76d9440`.

This pair uses a different frozen source/lock snapshot, cache state and phase
order from the earlier 59.11-second observation. Each pair is internally
controlled; their difference is not a causal estimate of the 20 renames alone.
Further pool optimisation needs focused compatibility, shared two-worker-cap
and coverage checks before another complete controlled comparison.

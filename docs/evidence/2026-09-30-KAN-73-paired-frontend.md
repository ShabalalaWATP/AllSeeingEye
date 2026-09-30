# KAN-73 controlled frontend comparison

Measured on 30 September 2026. The controlled comparison saved **59.11 seconds**,
below the acceptance target of 70 seconds. Both phases passed, selected the same
tests and produced identical coverage counts. This observation does not complete
KAN-73.

## Method

Both runs used the complete tracked source at
`ff3fb53d40165bafd3e649286450e7b7b5be5dba`, Node 24.21.0, pnpm 11.25.0,
two Vitest workers and one private Linux container limited to two CPUs and 6 GiB.
Dependencies and source remained fixed. The comparison changed only the unit
project's environment and setup to the former DOM defaults.

Each phase ran the same five-case infrastructure warm-up, restored the same
archived Vitest result cache, then waited ten seconds before timing. Filesystem
module caching was disabled. The order was Node followed by DOM. Other local
installation, test and measurement workloads were paused during the timed runs.
The archived source, lockfile, configurations and starting cache were checked
again after both runs.

| Measurement | Node | DOM |
| --- | ---: | ---: |
| Wall time, seconds | 853.6096593 | 912.7195997 |
| Passing files | 662 | 662 |
| Passing cases | 3,644 | 3,644 |
| Skipped files / cases | 1 / 1 | 1 / 1 |
| Covered lines | 19,981 / 20,538 | 19,981 / 20,538 |
| Covered statements | 22,461 / 23,357 | 22,461 / 23,357 |
| Covered functions | 7,323 / 7,766 | 7,323 / 7,766 |
| Covered branches | 20,266 / 21,988 | 20,266 / 21,988 |

Coverage changed by zero percentage points, satisfying the 0.05-point tolerance.
The timing criterion failed. No test scope or coverage threshold was reduced.

## Excluded observations

An initial frontend-only archive omitted a backend resource needed by five
infrastructure cases and failed. It is excluded from acceptance evidence.
A subsequent complete-source DOM run passed in 942.3500155 seconds, but its
starting result cache had not been archived. Comparing that run with the later
Node run would overstate the controlled saving, so it is also excluded.

## Evidence and next step

[Machine-readable results](2026-09-30-KAN-73-paired-result.json) record full hashes,
UTC start times, exit codes, coverage counts and acceptance flags. Raw logs,
LCOV, warm-up output, source archive, fixed cache and configuration copies are
retained outside the checkout in the owning worktree's parent directory.

The measurement uses an earlier frozen lockfile to keep both phases comparable;
it is not evidence of the current release dependency audit. Additional Node
candidates require focused compatibility checks and a new complete controlled
comparison before claiming the timing target.

# KAN-71: batch historical snapshot reflection

## Current whole-CI evidence

Exact-head CI `37005545521` on `30c57178` passed all 30 jobs. The four
PostgreSQL jobs took 581, 676, 631 and 958 seconds; their merger took 38 seconds.
The whole-job total is **48.0667 runner-minutes**, still above the required 30.
Parallel steps alone totalled 1,867 seconds (31.1167 minutes), serial steps 824
seconds, other job work 155 seconds and the merger 38 seconds.

This is a second observation after the earlier 53.7000-minute run, not a
controlled five-run comparison. Final-main fixture repairs, two additional
native tests, file partition changes and different hosted runners prevent
attributing the entire difference to one optimisation. No over-target five-run
campaign has been performed. KAN-73's separate controlled frontend result is
recorded in its own review note and does not offset this PostgreSQL shortfall.

## Focused implementation and safeguards

Historical row snapshots now reflect their requested ordinary tables together
into a fresh `MetaData` for each call. The same connection, transaction, requested
table order, primary-key row order and reflected value conversion are retained.
No inspector or metadata cache crosses calls, DDL or migrations. Independent
schema/constraint snapshots and explicit single-table inserts are unchanged.

A fresh ordinary-table-name preflight keeps the original per-table path for
missing names, duplicate names, views and temporary tables. In particular, a
conversion callback failure on an existing table still precedes a later missing
table error. Unexpected reflection failures propagate. If SQLAlchemy warns and
omits an unreflectable table, the helper retries its individual reflection to
recover the native exception, then refuses the incomplete batch even if that
retry unexpectedly succeeds. It never silently omits requested rows.

Batch reflection can resolve relationships between requested tables and occurs
before the first row query. The parity evidence therefore covers these actual
historical schemas and their pure UUID conversion hook; it is not a claim about
arbitrary stateful callbacks or unusual `NullType` foreign-key schemas.

## Correctness and selection

The private SQLite/PostgreSQL validation passed **62 tests, zero skips**. These
include 32 new cases covering complete migrated historical snapshots, UUID
conversion callbacks, reordered composite keys, one-shot name iterables,
duplicates, empty input, fresh rows/schema after DDL, missing-name/error order,
permanent and transient unreflectable-table failures, and view/temporary-table
fallback. Existing migration rollback, rekey, cancellation cleanup and real
coverage-reporting regressions also passed. Durability stayed enabled; source
hashes were unchanged; no private databases remained; the owned service was
removed without cleanup errors.

Full collection found 10,999 cases. The PostgreSQL selection is 2,867 cases:
2,491 parallel and 376 serial. Every one of the previous exact-CI 2,833 IDs and
all 2,363 older retained IDs survive. The 34 additions are the 32 new cases and
two existing SQLite reflection parameters now explicitly marked `db`. Their
additional validation cost is included in future whole-CI measurements. All
eight existing untracked node-ID evidence files retain their original hashes.

## Fixed four-arm mechanism comparison

The predeclared order was individual/batch/batch/individual, using the same four
original notification migration guard cases. Source, installed dependencies,
warm-up and cooldown were fixed. A private pinned PostgreSQL 16/PostGIS service
had two CPUs, 2 GiB memory and all three durability settings enabled. Pytest ran
in one process; inherited test/coverage controls were cleared and worker absence
was asserted. Coverage was disabled only for this bounded mechanism diagnostic.

| Arm               | Wall seconds |
| ----------------- | -----------: |
| Individual, first |      59.4165 |
| Batch, first      |      41.2726 |
| Batch, second     |      41.0631 |
| Individual, final |      57.4757 |

The median fell from 58.4461 to 41.1678 seconds: **17.2783 seconds (29.5627%)**.
All 16 case executions passed. Every arm retained the same 18 migrations, 38
independent `run` transactions, 18 schema captures, 22 row snapshots and exact
per-case requested/returned names and row counts. SQLAlchemy execution-context
attempts fell from 32,944 to 16,770. These are attempts, not individual SQL
statement counts; observer overhead scales with them. Full row/value parity is
proved by the separate correctness suite, not merely the timing records.

The Windows/Python 3.13 instrumented timings are diagnostic, not whole-CI
acceptance. Recorded boundaries overlap and must not be summed. All source and
evidence-code hashes remained unchanged throughout, and the owned service was
removed cleanly after the final arm.

## Covered parallel attribution

A separate single diagnostic passed the same 23 job-access, bell and health
cases selected by current CI, with two isolated workers and the real branch
coverage configuration. It retained raw arcs for 1,578 source files. The existing
CI shard options suppressed per-shard reporting and its partial-suite floor;
the ordinary 90%, combined and security floors were not changed.

The wall time was 52.2221 seconds. Ten cases used clones, 13 were ineligible and
no clone needed a later reset or schema drop. Nine app fixtures in the mixed
health test file spent 10.2306 seconds creating and 6.7586 seconds dropping
schemas. Forty-two fresh fingerprints consumed 3.4618 seconds; 19 fixture app
constructions consumed 4.5957 seconds. All 49 real Argon2 hashes and 26 real
verifications remained, consuming 3.3846 seconds. These nested worker boundaries
are not additive; the app metric excludes direct dev-docs construction. This
profile justifies examining redundant fixture work, not weakening eligibility,
security settings, coverage or retained test scope.

## Evidence and remaining acceptance

Raw manifests, source/dependency hashes, logs, JUnit, operation counts and arcs
are retained outside Git under the local `kan71-73-followup-58c5b2fe` evidence
directory: `ci-37005545521`, `snapshot-validation`, `snapshot-screen`,
`snapshot-census` and `covered-parallel`. Independent review covered the source
change, strict exception paths and both private profiling harnesses.

Fresh complete CI must measure this candidate. The under-30 whole-job criterion,
then five comparable whole-CI measurements, remains outstanding. No selected
case, assertion, coverage floor, isolation guard or PostgreSQL durability setting
was removed to obtain the bounded result.

# KAN-71: scoped native physical schema inventories

## Published baseline

The exact published `5cc7dbeb` full CI run
[37011600827](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/37011600827)
passed all 30 jobs. Its four PostgreSQL jobs and coverage merger took 2,723
seconds, **45.3833 runner-minutes**. The under-30 target remains unmet. The actual
retained census contains 2,867 distinct selected IDs (2,491 parallel and 376
serial), including every previously selected 2,833 ID and 34 explicit correctness
extensions. Runs on different hosts and with different test additions are not a
controlled causal comparison against earlier measurements.

## Narrow physical inspection boundary

The candidate removes repeated physical catalogue queries only from two
explicitly opted-in, privately owned historical PostgreSQL fixtures. The generic
per-table `schema_state` remains unchanged. A new inspector and six native
`get_multi_*` calls produce the complete columns, indexes, primary-key,
foreign-key, check-constraint and unique-constraint witness. Reconstruction
preserves original table order and all field/list content. It does not substitute
ORM metadata, cache inspectors across calls or omit independent physical evidence.

Admission requires the transient ownership marker set after the fixture's
successful private database creation, an effective query-free loopback asyncpg
URL with the exact generated UUID database shape, native inspector/dialect types,
matching connection/engine/dialect identity, and unmodified native method
functions and receivers. The marker is restored through a captured dictionary in
`finally`, including when a callback closes or invalidates the connection.
Generic, SQLite, unowned and injected-reflection callers retain the original
implementation.

A complete successful physical witness is identical. The native fast path does
not promise the same first error when several different reflection operations
could fail. Any native error propagates unchanged and invalidates the whole
snapshot, without replay, savepoints or a replacement transaction. Non-exception
incomplete/extra result maps use the original per-table operations over the
originally requested names, so disappearing tables cannot silently vanish.

## Correctness and review

The focused suite passed **115 cases with zero skips** in 150.11 seconds. It
includes the previous 62 snapshot, migration, cancellation and coverage-reporting
cases, plus 53 inventory/admission regressions. The latter cover complete physical
schema equality, current migration-head equality, real constraint behaviour,
fresh DDL, binding and method-override rejection, and ownership restoration.

The real PostgreSQL error regression retained the original division-by-zero
exception (`22012`), proved that the same transaction remained aborted (`25P02`),
and prohibited individual-path replay. The existing outer manager rolled back;
a later independent transaction succeeded. Separate native close/invalidate
cases and a failing-info-access regression preserve the original callback error,
restore the captured ownership dictionary and dispose the engine.

Ruff and formatting passed. Independent code and security reviews were clear
after repairing the initial native-method receiver check. The private durable
PostgreSQL service was removed, with zero remaining generated databases and no
cleanup error. Source hashes were unchanged throughout validation. These are
correctness results, not performance acceptance.

Raw manifests, hashes, logs and all 115 JUnit identities are retained outside Git
in the local `kan71-73-followup-58c5b2fe/schema-inventory-validation` evidence
directory.
The fresh selector census retained all 2,867 IDs from that successful CI and all
2,363 older retained IDs. It now selects 2,881 IDs (2,495 parallel and 386 serial),
adding precisely the eight parametrised physical-inventory and six native-error
cases. All eight historical node-ID evidence files remain untouched.

The separate health-fixture candidate is outside this measurement. No selected
case, assertion, coverage floor, isolation guard or durability setting is reduced.

## Fixed schema-only mechanism comparison

The predeclared order was individual/batch/batch/individual over the same four
original notification migration guard cases. Row snapshots, source, dependencies,
warm-up, cooldown and case identities were fixed. The private pinned PostgreSQL
service had two CPUs, 2 GiB RAM and 1 GiB tmpfs storage, with all three durability
settings enabled. This is separate from CI's storage allocation. Pytest used one
process and no coverage for this bounded mechanism diagnostic.

| Arm               | Wall seconds |
| ----------------- | -----------: |
| Individual, first |      40.3340 |
| Batch, first      |      28.2809 |
| Batch, second     |      28.6240 |
| Individual, final |      40.9664 |

The medians were 40.6502 and 28.4525 seconds: **12.1977 seconds (30.0066%)** lower
for batching. All 16 original case executions passed, with matching full physical
schema hashes, row snapshot names/counts and non-execution-context operation
counts. Source and evidence-code hashes remained fixed; no batch call fell back.
Native SQLAlchemy methods were not wrapped or replaced. An identical private
execution-context observer was present in both arms; its nested timings are not
additive, and its attempts are not individual SQL statement counts.

The launcher exited 1 after all measurements and successful container removal.
Its final absence check expected capitalised Docker error text, but this Docker
client returned lowercase `no such object`. The original failure is retained.
Separate owner readback checked the exact immutable container ID was absent and
the unique ownership-label census was empty. Create acknowledgement was complete,
with no unresolved operation. No measurement was retried or replaced following
this post-measurement verifier failure. Raw results and the separate cleanup
resolution remain in `schema-inventory-screen` for review.

Independent evidence review reconciled all four JUnit records, 18 identical
physical schema witnesses and 22 identical row summaries per arm. Execution-context
attempts fell from 16,770 to 5,738 per arm. The reviewer accepted the complete
diagnostic with the original launcher failure retained; it did not execute a new
live cleanup probe or claim whole-CI acceptance.

The measured working tree also held a separate health-fixture candidate in
`test_health_and_errors.py`, `health_app_factories.py` and
`test_health_template_classification.py`. Those files do not supply the selected
migration tests, their private migration fixture, the schema witness or the
profiling plugins. They were identical in all four arms. For schema-only
publication, their bytes were preserved with hashes outside Git, the tracked
health test was restored to the published baseline and the two held new files
were removed from collection. The complete dirty tree is not claimed to be
identical to the schema-only commit; its measured helper, migration-test, lock
and profiling inputs remain pinned by the raw source manifest.

After parking those edits, a separate collect-only closure check found the same
four migration cases, each requesting the private `migration_database` fixture
and none requesting `app`, `settings`, `client` or `container`. None of the three
held health modules was loaded. Selected helper/test, conftest, fixture-support
and lock bytes exactly matched the measurement manifest. Fresh collection of
the schema-only publication candidate found 11,052 cases and the same 2,881-ID
PostgreSQL scope, with all prior IDs retained. Its exact eight lane lists are in
`schema-only-census`; they supersede the earlier dirty-tree lane distribution.

The coordinator additionally queried the exact removed container ID at 14:18:59
UTC and retained an empty successful Docker census. That corroborates removal;
it does not rewrite the original launcher exit status.

The whole-CI under-30 target, five comparable qualifying runs and release approval
remain outstanding.

# Backend performance batch: KAN-28, 31, 33, 34, 35, 37, 38 and 39

Recorded 30 September 2026. Baseline: `69696286c45a905937f666f4056768c6f8087475`.
Branch: `codex/KAN-28-performance-batch`. This record describes implemented code
and local evidence, not release approval. CI, the combined branch and the remaining
deployment checks below must pass before release.

## Delivered behaviour

| Ticket | Change and behavioural evidence |
| --- | --- |
| KAN-28 | Each sampler cycle prunes every sample kind beyond 30 days in bounded 1,000-row delete statements. The `(hour, id)` index supports backlog removal. Tests retain the 10/29-day rows, remove 31/400-day rows for two kinds plus a 1,100-row backlog, and preserve in-window means. |
| KAN-31 | An attempt reuses validated frozen input and unchanged canonical payloads. Every row read hashes its actual bytes, compares stored integrity metadata and copies cached payloads before returning them. Heartbeats update only the lease with status/token/expiry/revision fences. Fresh owner, team, routing, linked-object, baseline and source checks remain on every operation. |
| KAN-33 | A small per-job/month usage projection is written in the checkpoint transaction. Indexed sums replace historical payload decoding; audit call lists remain intact. Generated parity covers 50 jobs, 21 call states across three months and two owners. Invalid receipts fail closed. Token aggregates use PostgreSQL `BIGINT`, including a regression for two individually valid maximum counters. |
| KAN-34 | Infrastructure and countries reuse validated bytes and weak content validators. Only authenticated, currently authorised matching requests receive empty 304 responses. Exact-route middleware exceptions preserve `private, no-cache`; errors and dynamic trackers remain `no-store`. The bounded two-entry cache refreshes when providers replace the catalogue snapshot. Reference caching was excluded because its version boundary was outside this change. |
| KAN-35 | Disaster, conflict, maritime, space, cyber, economy and Ukraine projections use shared bounded worker admission and captured event references. Cancellation retains the admission slot until the worker exits. Final source and session checks protect release; a source generation stamp rejects disable/re-enable sequences during a read. Pruning sorts survivors only on overflow; global eviction orders equal timestamps by event ID. |
| KAN-37 | Monitor listing uses three statements for count, monitors and grouped watches. Recovering 20 expired jobs uses two statements, including a fenced bulk update. Existing ordering, watches, revisions and expiry rules are retained. |
| KAN-38 | Retry polling starts with retry-wait editions and indexed latest attempts. Open-attempt partial index, job summary projection and embedding validity projection remove large payload/vector reads from polling. SQLite and PostgreSQL migration round trips preserve audit payloads. |
| KAN-39 | Validated PostgreSQL pool settings expose size, overflow and timeout with unchanged defaults 10/10/10. SQLite options remain separate. The local stream/worker probe reached 20 of 20 connections without timeouts, supporting configurability while leaving tuning to deployment measurements. |

## Trust boundaries and review

`ReportJob._payload_validated` is an internal constructor optimisation, used only
by `report_job_codec.with_payload` after canonical validation or an exact-byte
cache hit. Normal constructors and dataclass replacements still validate. The
codec computes SHA-256 and size from actual stored UTF-8 bytes on every read;
neither a row's stored digest nor revision alone proves integrity. Its one-entry
payload cache holds a private copy and deep-copies returned values.

`AttemptCache` is owned by one `ReportJobCheckpoints` instance. The checkpoint
gate binds it through a context variable and restores that binding afterwards.
Execution admission uses the same gate. Cache keys preserve JSON scalar types,
and reject tuple arrays in proposed mutations, preventing Python's `1 == True`
and `1 == 1.0` equality from skipping validation. Restored jobs are copied and
receive the current actor/profile. Source provenance caching covers evolving
collection, expansion, web and plan output, while enabled-source decisions and
authorised baseline evidence are freshly checked each time.

Reads decode before the administration lock where possible, then reload and
recheck authority, actual payload integrity, revision and lease state under the
lock. The lease-only SQL compare-and-set includes the expected revision, token,
running state and unexpired lease. It cannot renew an attempt superseded by a
checkpoint, pause or ownership change. No SQL session enters a worker thread.

The independent security reviewer found the numeric-type cache alias, a source
toggle ABA race and PostgreSQL aggregate overflow. All three were repaired.
Independent probes verified cache rejection and source generation rejection;
checked-in regressions and the PostgreSQL upper-bound test also passed. Invalid
recovery fixtures remain deliberately malformed raw database rows. Only fixtures
that were accidentally invalid for existing call-ledger rules were corrected.

Summary, usage and vector-validity fields are projections maintained by the
repository and migration. Direct database writes that bypass those boundaries
can make projections stale. Actual vector retrieval still validates vectors.
Source generation follows the existing single-process deployment contract;
out-of-process control writes retain the existing TTL limitation.

## Controlled benchmark results

Windows host, Python 3.13, isolated virtual environments, same base revision and
deterministic fixtures, no coverage and no live providers. Other workers deferred
heavy tests during paired unprofiled measurements. These are one local comparison,
not statistical production latency guarantees. Raw scratch logs are under ignored
`data/kan28-performance/`; commands and key results are retained here.

| Probe | Baseline | Changed |
| --- | ---: | ---: |
| 1.8 MiB synthetic checkpoint, first heartbeat | 109.283 ms | 41.914 ms |
| Same checkpoint, warm heartbeat mean over 10 | 122.149 ms | 21.382 ms |
| Reserve with 50 synthetic 150 KiB jobs, mean over 10 | 92.735 ms | 5.105 ms |
| 5,021,324-byte infrastructure catalogue, warm loop work | 94.103 ms | 0.001 ms |
| Offline 14-day economy briefing integration test | 19.00 s | 9.37 s |
| Complete briefing command wall time | 23.486 s | 11.436 s |

The briefing fixture improved 50.7% by pytest runtime, above the 35% target. It
exercises the real integration path with deterministic providers, not a live
14-day provider run. The heartbeat microprobe stubs authority to isolate codec
and persistence work, so its timings do not measure full authority checks. The
catalogue figure excludes authentication, network and proxy compression.

Separate cProfile runs counted `restore_job` 196 to 3, `collection_from_dict` 186
to 4, canonical payload validation 1,205 to 199, and row decoding entry 347 to 331.
The final profile ran under shared load, so profiled wall times are not compared.
Coroutine resume counts are not reported as function invocation counts.

The board fixture retains 60,000 deterministic records, 10,000 in each of six
categories, using a 30-day/15,000-record per-category budget. A 1 ms heartbeat
measures maximum loop gaps. It includes current satellite publication times and
no external feeds.

| Board or maintenance operation | Before total / gap ms | After total / gap ms |
| --- | ---: | ---: |
| Disaster | 49.009 / 64.572 | 70.110 / 33.647 |
| Conflict | 437.700 / 437.800 | 626.418 / 34.664 |
| Maritime | 36.464 / 36.581 | 48.077 / 26.046 |
| Space | 46.436 / 46.535 | 54.880 / 23.575 |
| Cyber tracker | 38.361 / 38.462 | 44.853 / 39.818 |
| Ukraine | 84.898 / 85.021 | 45.789 / 29.707 |
| Cyber | 520.674 / 63.704 | 386.608 / 47.403 |
| Economy | 158.030 / 158.145 | 118.073 / 31.978 |
| Initial prune | 110.899 / 111.072 | 48.263 / 48.466 |
| Steady prune | 84.502 / 84.609 | 43.954 / 44.064 |
| Over-budget 250-event upsert | 21.864 / 21.970 | 23.356 / 23.473 |

All affected board gaps were below 50 ms. Some total response times increased
because bounded snapshot projection favours event-loop responsiveness. Steady
pruning improved by 48% but **missed the 35 ms target**. Deterministic global
eviction has a small cost in this fixture. No hard timing assertions were added.

Reproduce from `backend`, using this branch's probe script for both checkouts:

```powershell
.venv/Scripts/python.exe ../scripts/benchmark_report_jobs.py --checkout BASELINE --rounds 10
.venv/Scripts/python.exe ../scripts/benchmark_report_jobs.py --rounds 10
.venv/Scripts/python.exe ../scripts/benchmark_report_jobs.py --checkout BASELINE --briefing
.venv/Scripts/python.exe ../scripts/benchmark_report_jobs.py --briefing
.venv/Scripts/python.exe ../scripts/benchmark_report_jobs.py --briefing --profile
.venv/Scripts/python.exe ../scripts/benchmark_boards.py --checkout BASELINE
.venv/Scripts/python.exe ../scripts/benchmark_boards.py
```

`scripts/benchmark_backend.py` also invokes the board/maintenance heartbeat probe.
`BASELINE` is a separate checkout at the revision above with its own dependencies.

## PostgreSQL and pool evidence

Private PostgreSQL 17.10 on localhost port 55428, separate test and migration
databases, no production environment or shared test database. The checked-in
`test_performance_postgres.py` probe seeds 10,000 attempts, 1,000 jobs and 1,000
embeddings and captures `EXPLAIN (ANALYZE, FORMAT JSON)`:

| Query | Planner choice | Execution |
| --- | --- | ---: |
| Due retries | Attempt primary key and `ix_subscription_attempt_history` | 0.125 ms |
| Stopped-attempt reconciliation | `ix_subscription_attempt_open` and job primary key | 0.105 ms |
| Job list | `ix_report_jobs_owner_created`, summary only | 0.181 ms |
| Search counts | Hash join and small sequential scans, no vector projection | 1.027 ms |

Search counts cover the whole 1,000-row fixture, so the planner sensibly chose a
sequential scan. The probe does not force index use to create misleading evidence.
The three selective recurring queries use indexes.

The opt-in pool probe uses 32 actual `LiveStream` generators (eight actors with
four streams each), three freshness cycles, and six worker query loops including
a controlled 25 ms database delay. It recorded **146 checkouts, peak 20/20,
zero timeouts**, completing the measured cycles in 0.522 s under shared host load.
It exercises session checks but excludes HTTP transport and external providers.
The first draft probe waited for a quiet stream to emit a frame and timed out;
the corrected probe publishes a public sequence advance each cycle and bounds
each wait to 30 seconds. That failed harness run is excluded from measurements.

```powershell
$env:ASE_TEST_DATABASE_URL='postgresql+asyncpg://postgres@127.0.0.1:55428/ase_kan28'
$env:ASE_PERFORMANCE_LOAD='1'
.venv/Scripts/python.exe -m pytest tests/test_performance_postgres.py --no-cov -q -s
```

Only use an owned disposable database: the app fixture recreates its schema.

## Validation and remaining gates

- Final cache, gate, cooperative board, event store and source-control set:
  **54 passed** in 11.90 s, with `--no-cov`.
- Storage, catalogue, migration, gate and affected route set: **46 passed**.
- Cancellation, source, lease, budget and retry set: **33 passed**.
- Generated monthly parity, malformed receipts and monthly budgets: **13 passed**.
- Store, cooperative read and discard storage set: **36 passed**.
- Catalogue, store, board and migration set: **22 passed**.
- PostgreSQL owner, worker, cancellation, monthly budget and stale-lease set:
  **26 passed**. Plan probe, aggregate upper-bound and corrected pool probe passed.
- SQLite migration valid round trip and malformed-row preflight cases passed.
  PostgreSQL 0068 downgrade to 0066/re-upgrade passed after the `BIGINT` repair.
- Strict mypy: **1,381 source files passed**. Backend Ruff and format checks passed.
  Bandit found no issues; import-linter kept all three contracts. File-length
  check and `git diff --check` passed. No coverage result or full-suite claim.

These runs overlap and must not be added as a unique test count. The final narrow
set protects the review repairs; the wider runs protect the surrounding behaviour.

Migration **0068 now follows security revision 0067** in the integrated stack.
The earlier standalone measurements used predecessor 0066. The combined SQLite
tests and a fresh private PostgreSQL database both passed upgrade to 0068,
downgrade to 0067 and re-upgrade. Alembic reports one head, 0068. Migration preflight identifies
invalid job IDs and fails closed before DDL; repair those audit rows before retry.

Release gates remain: complete combined CI/coverage and independent code review;
measure production baseline row counts before/after the first sampler cycle.
The original checkpoint missed the 35 ms steady-prune target; the controlled
follow-up below meets it on the documented repeated-prune workload.
No production requests, row counts, deploys or merges were performed.

Integration boundaries: architecture moves pool arguments into
`Container._initialise_database`; runtime adds read counters and worker-cycle
progress around `tick`, not heartbeat-based liveness. Preserve those changes when
stacking. Source-export changes to `_kev` do not overlap this branch's read path.

## Coordinator integration

Integrated security PR #92 at `744443bc`, including architecture/runtime and
the CI/test foundations. Pool options remain in `_initialise_database`, and
runtime read-rejection counters and worker progress are preserved.

To keep the store below the source-file target, pure per-category retention
decisions now live in `adapters/store/retention.py`. Category flags and the vessel
cutoff are computed once; non-space events avoid satellite-expiry checks. The
store still owns every index mutation and stream invalidation. Independent
review found no parity issue, and 21 satellite/vessel/FIRMS tests passed.

Integration validation passed 38 store/migration/runtime/cooperative/scheduler
tests and 57 board/catalogue/checkpoint/source/lease regressions. Full mypy
passes on 1,411 modules; OpenAPI/types were regenerated and TypeScript passes.
The post-extraction benchmark ran under shared load: it preserved 60,000 records
and all board gaps were below 50 ms, but its 73.926 ms prune timing is not a
controlled comparison. It does not replace the controlled table or establish
the 35 ms target. Full stack CI remains pending.

CI's Gitleaks 8.24.3 scan reported two false positives in the historical KAN-31
test commit. Both matches contain adjacent Python keyword arguments with a
runtime-generated UUID, not a literal credential. The current calls are split
over lines, and `.gitleaksignore` records only those two exact historical
fingerprints. All other files, rules and commits remain scanned.

## Proxy and browser acceptance

At frozen `1f99af37`, the actual Caddy image served byte-identical identity and
gzip catalogue bodies: infrastructure shrank from 5,021,324 decoded bytes to
608,312 bytes on the wire, and countries from 21,000 to 7,326 bytes. Both retained
the same weak ETag across encodings, `private, no-cache`, `Vary: Accept-Encoding`
and empty 304 responses. Invalid or non-matching validators returned 200;
unauthenticated and logged-out matching validators returned 401 with `no-store`.

Real Edge navigation, normal login and switching the nuclear layer off/on
produced a first 200 then 304 while restoring all 195 displayed records. The
browser used a leaf-certificate SPKI exception for the disposable local CA,
without changing operating-system trust or overriding requests or fetch.

The subsequent KAN-35 follow-up hoists satellite time boundaries once per
category, avoids allocating survivors when a category cannot exceed its cap,
and skips the full-store difference pass when no IDs were removed. Sixteen
event-store, satellite-expiry and FIRMS retention regressions and the three
affected modules' type checks pass. Independent review found no expiry, survivor
ordering or pending-removal regression.

A short controlled comparison used the tracked 60,000-event fixture,
`PYTHONHASHSEED=0`, three warm-ups and 20 steady-prune cycles, with other local
test workers paused. At `1f99af37`, median time was 31.361 ms (28.117-38.171 ms);
at `b7fb0d1b`, it was 20.844 ms (19.707-23.844 ms), a 33.5% improvement. All 20
follow-up cycles were below 35 ms and retained all 60,000 records. This repeated
prune-only protocol differs from the earlier board/heartbeat single-run
measurement; the two timings must not be presented as one direct comparison.

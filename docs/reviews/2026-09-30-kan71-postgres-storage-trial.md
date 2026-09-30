# KAN-71 PostgreSQL storage trial, 30 September 2026

The proposal mounts only the disposable PostgreSQL CI service's data directory
on a bounded 2 GiB tmpfs after the initial 1 GiB CI trial exhausted its capacity.
It retains automatic worker selection, the pinned image,
real transactions and the serial migration/race lane. A read-only preflight
requires `fsync`, `synchronous_commit` and `full_page_writes` to remain `on`.
Production database configuration, hashing implementation, test selection,
serial database URLs, coverage floors and existing artefact collection remain
unchanged.

This is a CI trial, not evidence that KAN-71's 30 aggregate runner-minute target
has been met. Run the trial with `--workers auto`; do not combine it with the
two-worker experiment. The coordinator owns the final workflow integration and
publication.

## Completed CI comparisons

Durations below sum the four PostgreSQL test jobs. Merger jobs are additional.
The parallel/serial columns are exact GitHub step durations; they do not separate
individual fixture setup, call and teardown costs. Every selected case passed.

| Run | Worker setting | Parallel steps | Serial steps | Other job time | Test jobs total |
| --- | --- | ---: | ---: | ---: | ---: |
| [36662274115](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36662274115) | auto, before collection fix | 2,818 s | 765 s | 143 s | 62.10 min |
| [36696097087](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36696097087) | auto, `cccfa79` | 2,504 s | 564 s | 157 s | 53.75 min |
| [36701253258](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36701253258) | two, `b6b83f7` | 2,827 s | 542 s | 150 s | 58.65 min |

The auto and two-worker runs each passed 2,092 parallel and 271 serial cases.
Two workers reduced the observed startup-to-collection markers to 31–49 seconds
from auto's 69–76 seconds, but aggregate job time increased by 9.1%. Individual
job times varied: two-worker shards 0–3 took 635, 984, 981 and 919 seconds. These
single CI runs do not establish variance or causality, but provide no measured
reason to retain two workers for the separate storage trial.

## Local schema and storage screening

The local probe ran between 10:19:59 and 10:23:54 UTC during an agreed CPU window.
It used the exact candidate later committed as `98b81319`, based on `cccfa79`.
The only helper change skips the 79 redundant existence queries after successful
SQLAlchemy `drop_all`. Fresh SQLite behaviour and SQLAlchemy DDL execution remain
unchanged. The coordinator cherry-picked that change as `a7a0f403`.

Two new disposable containers used the same image:

`postgis/postgis:16-3.4-alpine@sha256:681931a625df344215e9b8998bf34daf146b6a395ceacee4439eb9c85869239f`

Both reported PostgreSQL 16.4, had a two-CPU limit, 2 GiB memory/swap limit and
256 MiB shared memory. The baseline used the image's declared Docker anonymous
local volume, not overlay storage. The candidate mounted
`/var/lib/postgresql/data:rw,size=1073741824` as tmpfs. All three durability settings
were queried and asserted `on` in each service. The GitHub trial leaves its CPU
and memory limits unchanged; local hardware and Docker Desktop storage differ
from the GitHub Linux runners.

Each storage service ran one warm-up pair and three measured pairs, alternating
old/new helper order. Timings include `create_schema(fresh=False)` and
`drop_schema`, without coverage. Storage configurations ran sequentially. The
small sample and fixed storage order limit the strength of this screening result.

| Storage / helper | Measured cycles (seconds) | Median |
| --- | --- | ---: |
| Default volume / original | 3.558748, 3.757674, 3.834010 | 3.757674 s |
| Default volume / fewer checks | 3.385182, 3.578092, 3.741489 | 3.578092 s |
| Tmpfs / original | 1.458355, 1.456917, 1.397233 | 1.456917 s |
| Tmpfs / fewer checks | 1.466405, 1.282964, 1.293122 | 1.293122 s |

The safe helper change reduced the default-volume median by 4.8%. The tmpfs
candidate median was 63.9% below the default-volume candidate. Each original
cycle executed 237 SELECT, 206 CREATE and 79 DROP statements; each candidate
executed 158 SELECT, 206 CREATE and 79 DROP statements.

Outside timed sections, all 79 declarative table names found in the source
matched registered `Base.metadata`. Real PostgreSQL catalogue comparison using
Alembic, including server defaults, returned no differences. Repeated full-schema
resets preserved an unmanaged table and its committed row. Four new SQLite
regressions also cover fresh, empty, partial and populated schemas, defaults,
foreign-key/check enforcement, indexes, DDL hooks and unmanaged data. Together
with existing pytest-support tests, all nine passed in 1.24 seconds. Ruff check,
Ruff formatting and `git diff --check` passed for the schema commit.

Both private containers and their anonymous volumes were removed successfully.
The probe script and raw JSON are retained outside Git in the task's
`kan71-timing/profile_reset.py` and `kan71-timing/reset-profile-result.json`.

## Durability scope and trial acceptance

Tmpfs retains real PostgreSQL transactions, WAL, locking and committed data
across client reconnects and application-worker restarts. Its contents do not
survive host power loss or container stop/recreation. The existing test search
found no PostgreSQL process/host crash or power-loss test; worker restart tests
recreate application workers while PostgreSQL continues running. PostgreSQL
backup subprocesses are mocked. This suite does not establish crash recovery.

The revised CI mount is bounded to 2 GiB. A capacity failure must fail the run, never
switch off durability settings or omit tests. Keep the source/model inventory
checks and every selected PostgreSQL case. Compare executed node-ID artefacts
with the reviewed census, require all serial and parallel lanes and their merger
to pass, then record total test-job plus merger runner-minutes. A successful
Linux trial is required before claiming a CI improvement. The ticket's repeated
run acceptance remains outstanding.

The initial proposed workflow passed Actionlint 1.7.12 and `git diff --check`. A parsed
YAML comparison against the preceding commit confirmed that only the bounded
tmpfs option and durability assertion step were added.

## First Linux storage trial and bounded capacity repair

[Run 36703958590](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36703958590)
used the 1 GiB mount and failed all four PostgreSQL shards through storage
exhaustion. It is excluded from performance comparisons. The bounded local
screening did not exercise the sustained WAL volume of hundreds of concurrent
schema resets and was insufficient to establish the required CI capacity.

| Shard | WAL checkpoint started (UTC) | First logged datafile ENOSPC | WAL ENOSPC panic |
| --- | --- | --- | --- |
| 0 | 10:46:51.089 | 10:48:47.844 | 10:48:59.295 |
| 1 | 10:44:51.460 | 10:45:55.869 | 10:46:00.736 |
| 2 | 10:46:11.577 | 10:47:54.850 | 10:47:54.850 |
| 3 | 10:46:04.301 | During recovery at 10:47:24.511 | 10:47:21.108 |

No shard logged a completed runtime checkpoint before its panic. PostgreSQL
attempted recovery, then failed to extend relation files and stopped. Subsequent
connection-refused test errors followed this service failure. Init logs identify
PostgreSQL 16.4, 100 maximum connections and 128 MB shared buffers. No filesystem
usage or WAL/data byte split was captured, so an exact peak cannot be inferred.

PostgreSQL 16 documents a default `max_wal_size` of 1 GB as a soft limit; WAL may
exceed it under heavy load. Its defaults include `min_wal_size=80MB`, a five-minute
checkpoint timeout and completion target 0.9. These are documented defaults,
not values measured by the failed run. The failure is consistent with inadequate
combined data/WAL/checkpoint headroom, but does not establish that WAL alone used
the entire mount. [PostgreSQL WAL settings](https://www.postgresql.org/docs/16/runtime-config-wal.html#GUC-MAX-WAL-SIZE).

The repair doubles only the tmpfs capacity to 2 GiB and adds read-only settings
and storage diagnostics. Both test lanes sample filesystem space/inodes and
`base`/`pg_wal` disk usage every 30 seconds. Concurrent deletion during `du` or a
failed sample is logged and sampling continues. A ten-second per-sample bound
limits diagnostic delays. EXIT cleanup stops the owned sampler and its sleep,
while preserving the exact test-command exit status. Separate capacity artefacts
are uploaded even when a test lane fails; no credential or environment dump is
included. The existing coverage artefact step is unchanged.

Two GiB is an unproven bounded retry, not a claimed sufficient maximum. The next
Linux run must pass every selected case and show measured peak headroom before
any capacity or performance acceptance claim. Database flags, checkpoint/WAL
settings, workers, selection and coverage requirements are unchanged. No local
runtime probes or tests were run for this repair during the frontend benchmark.
Actionlint 1.7.12, Bash syntax parsing and `git diff --check` passed. Parsed YAML
comparison confirmed that the exact test commands and all other configuration
remain unchanged after removing the intended capacity/diagnostic additions.
ShellCheck was not available on PATH; no installation was attempted.

## Synthetic seeded-password component profile

The same window measured the real production Argon2 implementation against the
two fixed fixture passwords. Parameters remained time cost 3, memory 65,536 KiB,
parallelism 4, hash length 32 and salt length 16. Hashes were generated at runtime.
Twelve operations were measured per row on the Windows host, outside the
resource-limited PostgreSQL containers.

| Concurrent calls | Hash wall / process CPU | Verify wall / process CPU |
| ---: | ---: | ---: |
| 1 | 0.503 / 1.500 s | 0.481 / 1.469 s |
| 2 | 0.310 / 1.625 s | 0.298 / 1.781 s |
| 4 | 0.248 / 2.656 s | 0.230 / 2.844 s |

This isolates component cost, not total fixture CPU share or optimal CI worker
count. No fixture hash cache, production hash change or cheaper authentication
parameters were implemented. Production dummy hashes and password verification
remain unchanged.

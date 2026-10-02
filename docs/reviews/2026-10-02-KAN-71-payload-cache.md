# KAN-71: fresh checkpoint payload trees

`PayloadCache` now retains only the last successfully validated immutable byte
sequence. Every read parses a fresh JSON tree. This removes the retained mutable
tree and its repeated deep copy while preserving canonical validation for every
different byte sequence. Invalid replacements cannot replace the validated key.
Current-row length and SHA-256 checks still run before cache access on every read.

The patch changes only `report_job_codec.py` in production. Checkpoint locks,
current ownership and source authorisation, lease/fence checks, transaction
rollback, accounting and `AttemptCache` copies are unchanged. Independent code
quality and security reviews found no actionable issue.

## Behavioural validation

- All 13 new cases passed against unchanged source `597cedd5` before the change.
- The candidate passed 69 focused cases, including existing checkpoint,
  performance, accounting and usage regressions. Scoped Ruff, format, strict
  mypy and whitespace checks passed.
- A separate native PostgreSQL run passed all 18 selected cases, with 18 actual
  template clones, no fallback and no skipped cases. It used two workers with
  replacements disabled and a 450-second bound. This is correctness evidence,
  not a timing comparison or an aggregate coverage result.
- Both independent native-evidence audits reconciled source hashes, selected
  IDs, JUnit, durability settings, complete database catalogue equality and
  acknowledged exact owned-resource removal.

The new cases exercise nested alias isolation on cache misses and hits, JSON
type preservation, invalid replacement recovery, cancellation after a callback
mutates its proposed payload, rollback and subsequent successful commit,
changed leases, and a deactivated owner's real access policy. Configured model
or mail services are not called.

## Inconclusive fixed workflow comparison

One predeclared covered ABBA comparison used the complete tracked tree at
`597cedd51d39ae4b96b8ef23994b516bd362cdcf` as control. Its candidate differed only
by the reviewed codec bytes. Both 5,737-file source inventories, ZIPs, original
tests, guards, lockfiles, Python binary and 119 installed package versions were
sealed and independently verified. New regression tests were absent from both
timed trees and were validated separately.

Each arm ran the same excluded one-case warmup, two-second cooldown and eight
original workflow cases. Four workers, zero replacements, real authentication,
genuine branch coverage and a fresh private durable PostgreSQL service were
retained. Each service had two CPUs, 2 GiB RAM and separately 2 GiB tmpfs storage.
Every pytest process had a 450-second bound. There were no retries or reordered
observations.

| Arm | Source    | Recorded wall seconds |
| --- | --------- | --------------------: |
| 1   | Control   |           111.4358871 |
| 2   | Candidate |            99.9368562 |
| 3   | Candidate |           103.4854945 |
| 4   | Control   |           110.6865036 |

All 32 measured executions and four excluded warmups passed. Every arm passed
its source/runtime checks, complete catalogue comparison and acknowledged owned
cleanup. However, the final strict unchanged-module arc-equality gate failed.
The launcher retains exit 1 and `completed: false`, with four completed arms.
The recorded medians, 111.06119535 and 101.71117535 seconds, therefore do not
establish an accepted local saving.

Only the second arm added six unchanged-module arcs, with no lost arcs. They
map to an interrupted repository read during heartbeat lease renewal, its
rollback/re-raise path and the heartbeat cancellation handler. The other three
arms' unchanged-module arcs match exactly. This is consistent with cancellation
at a different scheduling point; aggregate arcs do not identify the exception
instance or prove its cause. Unchanged top-level codec function arcs match, and
each source's two codec arc sets match. All raw arcs remain available. The gate
was not relaxed and the failed result was not replaced with a successful one.

Both independent completed-evidence audits reconciled all 36 executions and
108 passed phases, the 1,578-file raw coverage records, the exact sealed sources,
interpreter and dependencies, and all four owned-resource removals. They accept
the correctness/provenance and clean failure preservation, while retaining the
comparison as failed and inconclusive. Neither audit reran the workload.

## Acceptance boundary and retained evidence

The latest complete hosted run before this change, CI `37043269376` at
`597cedd5`, passed all 38 checks but used **52.15 PostgreSQL runner-minutes**.
KAN-71 still requires at most 30 minutes and its five-before/five-after evidence.
Neither these cumulative profiles nor this inconclusive local comparison proves
that target. Fresh combined-source hosted CI is required after publication.

Normal integration merge `cd2baca6` incorporates released main `45381b2c`
without conflicts. The reviewed codec and both new test files retain their
exact hashes. A private frozen dependency sync then installed main's updated
versions; the 69 focused cases passed again, in 10.28 seconds, and repository
Ruff, scoped formatting and strict codec mypy checks passed. This later source
and dependency integration is outside the frozen comparison.

Private evidence is retained beneath
`C:/Users/alexo/.codex/scratch/kan71-73-followup-58c5b2fe/`:

- `payload-cache-597/` contains the before-change baseline and focused checks.
- `payload-cache-native/` contains the 18-case native manifest, JUnit and cleanup.
- `payload-cache-frozen/` contains both complete source archives and sealed inputs.
- `payload-cache-results/` contains every arm, raw coverage, original failed
  aggregate result and the recorded timings.
- `payload-cache-arc-diagnosis.json` is a separate read-only explanation. It does
  not modify the original result or acceptance policy.

The codec SHA-256 is
`facbc14cbc067e80addc8d1b954379aa0ba5b9bf0117682e9d08b8bd1e89c36d`;
the controls pin is
`9782158379d69a252b9c7df9b44ed1e24c08d62f29a5747257c2810524194737`.
Documentation and later main integration are outside the frozen comparison.

# KAN-71: select native cases before assigning shards

## Behaviour

The previous file planner assigned every backend test file before PostgreSQL
marker selection. Adding database-free tests could therefore move unrelated
native cases between shards. This milestone collects the two existing native
lanes first, then assigns only their selected cases to four shards per lane.

The upstream `postgres-plan` job uses the same frozen dependencies and existing
classification, including transitive fixture and owned-migration admission. It
runs collection only, without a PostgreSQL service or test fixture execution.
Files remain whole. Positive selected-case counts are deterministic scheduling
weights, with stable filename and shard-index tie breaking. Counts are not
duration predictions.

The marker expressions remain:

```text
parallel: (db and not (postgres or migration or race)) or owned_migration
serial:   (postgres or migration or race) and not owned_migration
```

The manifest binds actual Git source bytes, HEAD, interpreter bytes/version and
installed package names/versions. The consuming job requires its separately
published SHA256, complete deterministic partition and exact selected IDs.
Controller and worker hooks check input identity and selection before fixtures
run. Missing, extra or duplicate IDs, stale inputs and changed lane options fail
closed. There is no fallback to another assignment and no worker replacement.
Identity checkpoints detect drift, not hostile changes restored between reads.
Installed package identities do not attest every installed package byte.

The PostgreSQL test bodies, authentication, database isolation, durability,
template admission, migration classification and coverage configuration are
unchanged. SQLite keeps its original file weighting and coverage gates. The
native planner job is included in the required PostgreSQL result and must be
included in all subsequent whole-workflow cost comparisons.

## Validation retained before publication

- 18 focused planner/guard tests passed, including actual two-worker pytest
  subprocesses. An accepted control ran its two fixtures. Invalid digest,
  changed source and missing, extra or duplicate worker IDs were rejected before
  a fixture sentinel executed.
- All 14 existing shard-runner tests passed. Scoped Ruff, formatting, workflow
  Prettier, YAML parsing and whitespace checks passed. Actionlint was unavailable
  locally and is not claimed as local evidence.
- One complete Linux collect-only validation recovered the sealed population
  from CI run `37495020660`: 2,528 parallel and 368 serial IDs, including the two
  previously skipped cases. Each ID appeared once in its original lane. The
  eight guarded partitions contained 632 parallel or 92 serial IDs each, with
  no additions, losses, duplicates or lane changes.
- That run used the exact `de96da19` base plus the reviewed seven-file prototype,
  a portable real Git checkout and unchanged Python/package/source inventories.
  Both host and Linux input readbacks matched. It ran from 19:21:27 to 19:24:10
  UTC on 6 October 2026. The outer 162.950 seconds includes nested planner and
  guard scopes; those durations are not additive benchmark evidence.
- All 11 Windows client jobs and 13 Linux process-group receipts closed. The
  immutable container was absent, its owner census was empty and cleanup had no
  errors or unresolved operations. No test body, native database service or
  application fixture ran in this collection validation.

Private evidence remains retained under `collection-execution-v2`. Its result
SHA256 is `06ecff1dd5ff42004087d6a10225e8fd5c9c943713b13cae65314c3c5cd026a4`;
the sealed readback is
`e231a8d7f44274d4e21ad988ee7b76b8cc757efe25189751b93dbc39b392ddb5`.
The planned manifest SHA256 is
`c5a78b71807a7103596b425338100f3c2d1b70c64f0e84a12dac8b3cf5d58221`.

Earlier failed preparations and the first collection remain preserved. The
first collection exhausted the unchanged 600-second aggregate guard deadline
after three valid partitions while reading source through a Windows bind.
The successful successor used byte-identical source and real Git metadata in
an immutable Linux image layer, retaining every identity check and deadline.
This does not isolate a performance cause or establish a whole-CI saving.
A separate file-only readback verifier initially indexed stored command arguments
incorrectly; its failure was retained and corrected without a collection rerun.

The first published CI run, `37522070768`, was rejected before any job started:
GitHub does not allow `runner.temp` in a job-level environment declaration.
The repair places the identical manifest path in each consuming step's
environment, where the runner context is supported. Manifest digest, test
commands, isolation and all acceptance criteria remain unchanged. This failed
workflow compilation is not a native execution or cost observation.

## Remaining KAN-71 acceptance

This is a validated selection/assignment milestone, not completion of KAN-71.
Hosted CI must execute the actual native test bodies on the new assignment and
reconcile all original IDs, skips, isolation and coverage artefacts. The unchanged
SQLite 90 percent coverage gate must pass. Count balancing alone does not prove
balanced runtime or reduced total work.

The original whole-native target remains at most 30 runner-minutes, including
the new planner, all four native jobs and their merger. The required five
comparable before/after whole-workflow observations are still outstanding for
this change. No thresholds, assertions, authentication work, native cases or
coverage requirements were removed to obtain this collection result.

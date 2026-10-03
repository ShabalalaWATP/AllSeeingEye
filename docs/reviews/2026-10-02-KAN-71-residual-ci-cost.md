# KAN-71: residual PostgreSQL CI cost

## Complete CI baseline

Draft PR #121's exact-head run `36997668645` on `e273b44c` passed all 30 jobs.
Its separate SBOM workflow also passed. The four PostgreSQL jobs consumed 981,
721, 833 and 654 seconds, plus 33 seconds for the merger: **53.7000 runner-minutes**,
above the required 30. Parallel steps totalled 1,974 seconds, serial steps 1,048
and other job work 167. These figures use the whole-job protocol.

The selected census contains 2,473 parallel and 358 serial cases. There were
2,127 clones, zero acquisition schema fallbacks and 345 ineligible cases; one
parallel case skipped. Older whole runs have different feature source and case
counts, so they are historical context, not controlled comparisons.

## Bounded diagnosis

A private diagnostic passed 23 existing job-access, bell and health cases. Its
ten clones had no later prepare resets or schema drops. Forty-three fingerprints
consumed 1.27 seconds, ten clone commands 0.52 seconds and unchanged Argon2
hash/verify calls 3.62 seconds. Nine app cases excluded by conservative mixed-file
classification spent 8.74 seconds creating and 6.25 seconds dropping schemas.
These instrumented boundaries overlap and must not be summed. No eligibility
guard was relaxed.

The four notification migration guards were then measured in predeclared
recursive/target/target/recursive order. The source, installed dependencies,
warm-up, private durable PostgreSQL service and single test process were held
constant. All four arms passed the same four cases with zero skips, unchanged
source hashes and zero remaining private databases. Both owned services were
removed after their respective runs.

| Reflection                    | Wall seconds |
| ----------------------------- | -----------: |
| Recursive, first control      |     108.9724 |
| Target only, first candidate  |      59.0624 |
| Target only, second candidate |      59.3861 |
| Recursive, final control      |     111.0894 |

The median fell from 110.0309 to 59.2243 seconds, a 50.8066-second (46.1749%)
reduction. Both configurations requested 1,749 target reflections. Recursive
reflection loaded 6,106 tables in total, while target-only reflection loaded
1,749. Every arm retained 18 migration calls, 38 independent `run` transactions,
18 schema captures and 22 row snapshots. No inspector or metadata cache crosses
a migration. These local Windows measurements disabled coverage and diagnose a
mechanism; they do not establish whole-CI acceptance on GitHub's Linux runners.

## Focused changes

The historical-table helper sets `resolve_fks=False` for explicit target DML.
Independent schema snapshots still inspect every foreign key, and actual database
constraints remain enforced. New regressions cover typed/defaulted values,
composite-primary-key ordering, savepoint recovery after native FK rejection,
cascade deletion and fresh reflection after `ALTER TABLE`. Fail-before evidence
records the unwanted loading of the related parent table.

Pinned pytest-cov 7.1.0 merges report options. A configured `term-missing` survives
a later empty `--cov-report=`, causing every shard to analyse the source for both
total and terminal reports before the combined job repeats that work. Removing
the explicit report option and setting `coverage.report.show_missing=true`
preserves ordinary local output while honouring the existing quiet shard option.
Collection, branch tracing, exclusions, the default 90% floor and every combined
and security floor are unchanged.

The actual subprocess regression reproduced the unwanted report before the
change. It then passed with identical raw branch arcs, preserved combined data,
ordinary missing-line output and both ordinary and combined below-90 negative
gates failing correctly. This validates the report boundary without estimating
an unmeasured whole-CI saving.

## Validation checkpoint

Independent static review found no actionable issues. The initial focused SQLite
and subprocess checks passed three cases with two expected native-PostgreSQL
skips. The final private native run passed all 30 cases with no skips: historical
notification and rekey migration consumers, cancellation cleanup, the new typed
reflection and native-constraint regressions, and the real coverage subprocess
regression. PostgreSQL durability stayed enabled, source hashes stayed unchanged,
no private databases remained and the owned service was removed successfully.

Selection and sharding regressions passed 29 cases plus 14 subtests. Full
collection found 10,967 cases and selected 2,833 for PostgreSQL: 2,473 parallel
and 360 serial. All 2,831 IDs from the previous complete CI and all 2,363 older
retained IDs survive. Only the two new native reflection regressions were added.
The eight existing untracked census files retain their exact hashes.

Ruff, formatting and whitespace checks passed. Final released main `13e9525d`
was integrated by normal merge `aa0e7602`; its production code, dependency locks
and the reviewed performance guards were preserved. Fresh current-head CI and
its whole-job measurement remain required. These local correctness checks and
bounded profiles do not meet the under-30 runner-minute criterion.

Raw manifests, logs, JSON boundary timings and JUnit results are retained outside
Git under the local `kan71-73-followup-58c5b2fe` evidence directory, principally
`ci-36997668645`, `residual-parallel`, `residual-reflection`, `residual-validation`
and `residual-census`. The manifests
record source/dependency hashes, pinned service image, resource limits and
ownership identities. No failed or unmatched observation establishes acceptance.

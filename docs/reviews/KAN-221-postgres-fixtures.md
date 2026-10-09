# KAN-221: PostgreSQL version-link fixture repair

The `postgres-tests (3)` job on PR 177 failed in test setup, before checking the
version-link responses. The failed job was
[114064402848](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38001483308/job/114064402848).

Two unavailable-version fixtures violated PostgreSQL foreign keys:

- The deleted-version case removed a version still pinned by a subscription
  edition. PostgreSQL correctly refused the deletion.
- The wrong-report case assigned versions to a random, unpersisted report UUID.
  PostgreSQL correctly refused the missing parent.

The test repair keeps production code and constraints unchanged. The wrong-report
case now uses another persisted report visible to the same owner, so the HTTP
checks still exercise an incorrect report/version pair. Missing version IDs are
tested through transient schedule and edition domain objects at the projection
boundary, using the real access policy and SQL lookup. A newer saved version
remains available; all missing version numbers must remain null. This does not
claim that PostgreSQL permits deleting a pinned edition's version.

The shared history helper explicitly enables and checks SQLite foreign keys,
preventing these invalid fixture mutations from silently passing locally again.
Denied access, another account's subscription, exact historical versions and
ambiguous legacy version numbers retain their existing response checks.

## Validation

- The original six cases reproduced both CI errors against a new disposable
  PostgreSQL container: two failed and four passed in 25.57 seconds.
- The repaired six cases pass on SQLite with foreign keys enabled in 11.60
  seconds, and on PostgreSQL in 26.21 seconds.
- Ruff check and format check pass for the changed test file.
- Independent source review by the coordinator found no actionable issues.
- These are focused `--no-cov` runs; no new coverage percentage or full-suite
  result is claimed. The original PR's other checks were already passing.
- No production, schema, migration, API contract or dependency changes were made.

The PostgreSQL container uses CI's pinned PostGIS 16 image, private tmpfs data and
an ephemeral loopback port. Each test process clears inherited shared database
variables; only the PostgreSQL run sets a URL for this newly created database.
No shared database, application server, live provider or browser runtime is used.
The disposable PostgreSQL container and its tmpfs data were removed after testing.

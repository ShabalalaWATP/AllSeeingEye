# KAN-220: notification rollback fixture and retained evidence

The historical PostgreSQL notification rollback test upgraded a seeded legacy
alert to the current schema, then immediately downgraded to `0088`. Migration
`0094` correctly backfills a consumed-evidence marker for that alert and refuses
to discard retained markers. The resulting
[`postgres-tests (2)` failure](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38010083166/job/114092189919)
was a stale rollback precondition, not a production migration defect.

The test now first attempts the downgrade and verifies that its refusal preserves
the complete owned schema inventory and every table's rows. It then verifies the
single synthetic marker's rule, versioned empty payload, count and legacy cutoff,
and exercises the real retention adapter. The marker remains at the inclusive
seven-day boundary and expires one microsecond later. Both outcomes are committed
before continuing the original notification rollback sequence. All original
dropped-table, legacy-record, re-upgrade and backfill assertions remain.

No production migration, retention rule, database constraint or test threshold
changed. The retention operation runs only against the test fixture's fresh UUID
database. It does not clear a configured application database or bypass the
downgrade guard.

## Validation

- Before the repair, the single historical rollback test reproduced the exact
  retained-evidence `RuntimeError` on native PostgreSQL: one failure in 3.82 seconds.
- After the repair, seven tests passed in 42.73 seconds across
  `test_notification_migration_postgres.py`,
  `test_notification_migration_guards_postgres.py` and
  `test_warning_consumption_migration.py`. These cover six native PostgreSQL
  cases and the SQLite `0094` upgrade/retention-guard case.
- Focused Ruff lint and format checks passed. The changed test is 303 lines.
- Independent read-only review found no actionable issues in the retention
  boundary, owned-database scope, resource handling or preserved assertions.

The run used a single test process, frozen offline dependencies and a private
PostgreSQL 17.10 container bound to loopback port `25484`. Shared database
environment variables were cleared; only the dedicated notification-migration
fixture URL was supplied. All UUID databases were removed by fixture teardown,
then the labelled disposable container was stopped and its removal verified.
No providers or delivery senders ran. Full repository CI remains with the
coordinator; this targeted test-only repair did not measure coverage.

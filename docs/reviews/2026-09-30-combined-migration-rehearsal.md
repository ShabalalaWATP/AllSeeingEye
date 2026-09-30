# Combined migration rehearsal, KAN-110

Prepared against committed integration checkpoint
`dbdd83a88bdaae0017f49d8a1bb847d3f0beb0ff` in a separate managed worktree. The
forecast repair `4dc915c3597a20e089c88aa4d350b6dd736f7d09` was applied locally as
`57562a58` before the combined acceptance checks. This adds the pre-DDL guard for
retained alert baseline evidence and corrects historical schema projections.

The intended chain is
`0067 -> 0068 -> 0069 -> 0070 -> 0073 -> 0071 -> 0072 -> 0074`.

## Isolation and checks

The dedicated PostgreSQL tests require
`ASE_NOTIFICATION_MIGRATION_POSTGRES_URL` to name an owned disposable server on
loopback. Each test creates and removes its own UUID-named child database. Tests
use real Alembic migrations and reflected historical tables. They do not use
`Base.metadata.create_all`, application workers, notification transports, live
credentials or production data.

The checks cover empty upgrade and round-trip schema parity, preserved legacy
invitations and accepted-only sender receipts, canonical job checkpoint bytes and
monthly usage projections, valid and invalid embedding projections, original
alerts, schedules, editions and delivery history. Notification migrations leave
existing accounts unenrolled. Real PostgreSQL constraints reject duplicate digest
days, invalid windows and hours, exhausted attempt counts, duplicate route/device
deliveries and unknown device references. Device deletion cascades to push intents.

The explicit feature downgrade checks remove new notification settings and delivery
history, while preserving old records. This destructive feature reset is exercised
only on generated fixtures; an ordinary application rollback should retain the
additive tables. The 0067 privacy downgrade barrier is intentional.

Refusal tests assert unchanged schema, data and Alembic revision after a corrupt
legacy checkpoint, retained feedback, a retained ratio snapshot whose rule was
edited or deleted, and an attempted downgrade through 0067.

## Execution evidence

The benchmark window was explicitly released before dependency setup, container
creation or test execution. The private virtual environment used `uv sync --frozen`.
The labelled container used the repository-pinned image
`postgis/postgis:16-3.4-alpine@sha256:681931a625df344215e9b8998bf34daf146b6a395ceacee4439eb9c85869239f`
and reported PostgreSQL 16.4. Only loopback port 50346 was published. Runtime
limits were two CPUs, 768 MiB memory and 128 processes.

Inherited application/test database variables were removed from each test process.
The new suite used `ASE_NOTIFICATION_MIGRATION_POSTGRES_URL`; the historical
monitor/inventory suite used `ASE_MONITOR_MIGRATION_POSTGRES_URL`. Both named the
same owned server, and both fixtures created unique child databases. No shared
application test fixture or existing developer database was used.

From `backend/`, the initial repaired-chain run passed six tests in 137.28 seconds:

```text
uv run pytest tests/test_notification_migration_postgres.py tests/test_notification_migration_guards_postgres.py --no-cov -q -x
```

An independent read-only review by the forecast owner confirmed the isolation,
historical fixture and preservation boundaries. Its one improvement was applied:
schema snapshots now record primary-key constraints explicitly, alongside columns,
indexes, unique constraints, foreign keys and checks.

The expanded run with that improvement produced 16 passes and one failure in
186.14 seconds:

```text
uv run pytest tests/test_notification_migration_postgres.py tests/test_notification_migration_guards_postgres.py tests/test_annotation_monitor_migration_postgres.py tests/test_annotation_inventory_migration_postgres.py --no-cov -q
```

All six combined tests and all five historical inventory tests passed. The remaining
existing 0030 PostgreSQL parity test independently cloned the current ORM schema,
so it expected the four alert columns introduced by 0069/0070. This was reported
to the forecast owner for a correction to its historical metadata projection.
The forecast owner's follow-up `d505d8b7d9768eb0013706722bbb7a0b5937415e`, applied
locally as `b8a55bbc`, replaces that independent clone with `metadata_0030()`.
The previously failing case then passed in 4.49 seconds:

```text
uv run pytest tests/test_annotation_monitor_migration_postgres.py::test_postgres0030_preserves_acknowledged_origins_and_roundtrips --no-cov -q
```

Together, the expanded run's 16 unaffected passes and the repaired case cover all
17 selected cases successfully. The complete 17-case command was not repeated
after the one-file historical test projection correction. No production migration
defect remained in these scenarios.

After the final run, a database catalogue query confirmed no generated migration
databases remained. Cleanup verified the container ID and task/disposable labels
before removing `ase-kan110-migrations-7b59ba3213`, its volumes and the external
temporary file holding the generated connection state. No test workloads or
container resources remain from this rehearsal.

Ruff lint and formatting checks pass for all three new Python files. The repository
file-length check passes with existing warnings; all new files are below 350 lines.
These are focused migration checks with `--no-cov`, not a coverage measurement,
production-data rehearsal, live-delivery test or performance acceptance result.

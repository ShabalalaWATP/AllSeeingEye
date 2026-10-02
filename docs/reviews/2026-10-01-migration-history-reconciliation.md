# Migration history reconciliation, KAN-110

Main at `9ae40e3d` has the released chain `0066 -> 0075 -> 0076 -> 0077 -> 0078 ->
0079 -> 0080 -> 0081`. The unmerged Codex stack at `355b2305` instead contains
`0066 -> 0067 -> 0068 -> 0069 -> 0070 -> 0073 -> 0071 -> 0072 -> 0074`.
Neither graph has a missing predecessor or duplicate revision. Combining them
without reconciliation produces two heads. All 64 shared migration files have
identical Git contents.

No Codex production migration had occurred, and its earlier test databases were
confirmed disposable and removed. Only those unmerged migrations are renamed:

| Previous | New | Parent | Feature |
| --- | --- | --- | --- |
| 0067 | 0082 | 0081 | Invitation privacy receipts |
| 0068 | 0083 | 0082 | Performance projections |
| 0069 | 0084 | 0083 | Alert feedback |
| 0070 | 0085 | 0084 | Frozen indicator ratios |
| 0073 | 0086 | 0085 | Forecast reminders |
| 0071 | 0087 | 0086 | Notification delivery |
| 0072 | 0088 | 0087 | Alert routing |
| 0074 | 0089 | 0088 | Browser push |

The stage commits belong to PR92, PR93, PR94 and PR96 respectively. Main's
migration files are unchanged. In particular, `0075.down_revision` remains
`0066`. Every renamed migration's `upgrade` and `downgrade` function has the same
AST as its original at `355b2305`. The performance migration's error diagnostic
names its new revision; the privacy and frozen-evidence refusal logic is retained.

## Isolated validation

The validation checkout deliberately does not merge main application code. A
private directory outside Git contains copies of the scratch migrations plus the
unaltered main migrations. The test launcher redirects Alembic's script directory
to that combined graph. Tests that construct their own Alembic configuration use
the same directory override. No migration operations, schema checks or application
data are mocked. An integrated checkout needs no directory override.

`test_rekey_migration_history.py` uses actual migrations and reflected historical
tables. Its SQLite databases are private files. PostgreSQL uses the existing
fixture that creates a unique child database per test and removes it afterwards.
Inherited application and test database variables are removed from each process.
The only enabled database variable is `ASE_NOTIFICATION_MIGRATION_POSTGRES_URL`,
pointing at the owned loopback server.

The container uses the repository-pinned PostgreSQL 16.4 image, two CPUs, 2 GiB
memory and 128 processes. Its task/disposable labels identify ownership. Checks
confirmed `fsync`, `synchronous_commit` and `full_page_writes` were all enabled.
No application workers, live credentials or notification transports were started.

The first combined run passed 13 cases in 209.63 seconds, with `--no-cov`:

- The graph has one head, `0089`, and retains the released parent chain.
- Fresh upgrades leave accounts unenrolled and repeated upgrades change nothing.
- Populated `0081` upgrades preserve board subjects and mentions, evaluation
  artefacts, citation verdicts, team-copy provenance, resumed rules, bell settings,
  legacy checkpoint bytes, invitations, frozen alerts and delivery history.
- Existing schema columns, indexes, keys and constraints are retained.
- Corrupt checkpoints leave no partial performance-projection DDL. SQLite keeps
  the completed `0082` privacy revision; PostgreSQL rolls back to `0081`. Repairing
  the checkpoint and retrying reaches `0089` without losing the retained records.
- Privacy and frozen-ratio downgrade refusals preserve schema, rows and revision,
  including alerts whose rules were changed to absolute mode or deleted.

Two subsequently added cases passed separately in 15.74 seconds. They seed
explicit briefing, legacy media, unknown and invalid frozen origins, each with
an exactly 8 KiB original summary. The upgrade preserves the original payload,
digest, size and complete summary. These cases protect checkpoint integrity;
derived-origin behaviour belongs to the separate polling compatibility repair.

The existing migration regression selection passed 28 cases in 239.14 seconds:
invitation receipts, performance projections, alert feedback, frozen ratios,
forecast reminders, historical annotation monitoring, alert routing and the
PostgreSQL notification refusal suite. These tests also used `--no-cov`.
Ruff lint and formatting checks pass for all 18 changed Python files. The new
history test file has 309 lines.

After validation, a catalogue query confirmed no generated migration databases
remained. Cleanup checked the container ID and task/disposable labels before
removing that container, its volumes and the temporary credential files. No test
processes or PostgreSQL resources remain from this validation.

## Integration limits

The independent history tests use both real database engines, but they do not
replace a final model-to-schema comparison after main's models are integrated.
The full notification migration parity suite must run on that final source.
Likewise, the separate `compact_summary` backfill adjustment needs combined
migration validation and updated expected derived origins after it is applied.

The earlier rehearsal report records the original revision IDs and remains
historical evidence. These checks do not migrate a production database, prove a
production backup recovery or authorise an application rollback across privacy
or retained-evidence barriers.

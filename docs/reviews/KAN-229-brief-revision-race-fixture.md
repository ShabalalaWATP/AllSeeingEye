# KAN-229 valid pinned-revision race fixture

[PR 190 PostgreSQL shard 2](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38010088859/job/114088346614)
failed the pinned-identity race fixture before reaching its compare-and-swap
assertion. The fixture changed a schedule from Brief revision 1 to revision 2
without creating revision 2, violating `fk_schedules_brief_revision`.

The same failure reproduced on the KAN-229 branch at `9d6cb68c`: one failed test
in 2.66 seconds on isolated PostgreSQL 17.10, and one in 2.46 seconds on SQLite
after explicitly enabling foreign keys on the test connection.

The fixture now creates the second revision through the signed-in owner's
existing Brief revision endpoint. It checks the schedule still holds revision 1
before the simulated concurrent writer pins revision 2. Both original refusal
assertions remain: the stale settings edit cannot overwrite either the newer
pin or an archive transition. A direct SQL read additionally verifies that the
newer pin and original name survive the rejected edit. SQLite foreign keys are
enabled and checked for this test's connection; production constraints and
application code are unchanged.

Validation covered the complete race file and the existing editing test for
retained history, paused state and pinned identity:

- SQLite-configured group: 8 passed in 5.36 seconds.
- PostgreSQL-configured group: 8 passed in 13.53 seconds. Six cases use native
  PostgreSQL, with the existing standalone SQLite-writer race and SQL-compilation
  control retained in the same file.
- Ruff, formatting and `git diff --check` passed. The touched file is 206 lines.
- Independent source/security review found no actionable issue and confirmed
  the valid same-Brief scope, initial pin assertion and unchanged race checks.

The native run used a private disposable container, loopback port and isolated
worker database. No shared database or provider was accessed. Zero worker
databases remained afterwards, and the owned container was removed. The full
backend suite and coverage were not rerun for this fixture-only correction.

# KAN-169 lifecycle fixture repair

PR 189 at `1763c790642529fd1e380f0387a892bcf5073853` failed backend shard 4
in `test_lifecycle_loads_before_feeds_and_saves_after_they_stop`.
The lifecycle's synthetic settings supplied only `feeds_enabled`; startup now
also reads `enterprise_enquiry_retention_days` when scheduling housekeeping.
The resulting `AttributeError` occurred before the original ordering assertions.

The fixture now supplies a non-default retention of 90 days and exposes its
existing expiry mock to the test. The test also checks that startup passes the
exact session factory, clock and configured retention to housekeeping. Snapshot
restore, feed startup/shutdown, snapshot save, disposal and partial-startup
assertions are retained. Production behaviour and retention defaults are unchanged.

The CI failure is the before-fix evidence:
[backend shard 4](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38008132990/job/114081601692).
Independent source review confirmed the fixture matches the expiry signature and
preserves the lifecycle checks. Validation on 10 October 2026:

- `uv run --frozen --offline pytest tests/test_live_snapshot_service.py --no-cov -q`:
  all 12 tests passed in 1.17 seconds.
- Ruff checking and formatting passed for the changed test, as did `git diff --check`.

The private editable environment resolves to this worktree. Shared database test
variables were removed from the test process; no external database or service ran.
Coverage was not remeasured for this fixture-only change. CI remains responsible
for the complete suite and unchanged coverage gates.

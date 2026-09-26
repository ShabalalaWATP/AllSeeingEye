# Standalone annotation monitoring

Status, 8 September 2026: integrated on main at `0c91741` with registry routing;
local, PostgreSQL and repository checks passed; combined backend acceptance passed
3,278 tests, with 55 skips and 95.06% coverage. The integrated frontend passed
1,009 tests with 90.11%
branch coverage, and the production build passed on that tree. The broader
requirements are preserved in ANNOTATION_COMPARISON_PLAN.md.

## Operator workflow

Open a saved report version and create a monitor from one to twenty selected
claim, identity or organisation-review roots. The selection must contain their
current revisions when saved. Give it a name and choose applicable notification
categories. Creation captures the baseline silently; notifications are opt-in.
A selected-root monitor does not automatically discover new annotations.

### Whole-report inventory mode

Integrated from `3ef66e9`: full backend acceptance passed 3,291 tests, with
70 skips and 95.05% coverage; 24 independent PostgreSQL cases and 1,018 frontend
tests also passed. The merged runtime tree is identical to that accepted tree.

The new creation flow also offers all annotations on one saved report version.
It can start with no annotations and follows new claim, identity and organisation
review roots as they are added. The server captures the complete current baseline;
notification categories remain available even before that category has a root.
The mode cannot be changed after creation. It does not follow new report versions.

The twenty-root limit applies across all three kinds, including withdrawn roots.
A report already above that limit cannot start an inventory monitor; select
specific annotations instead. Adding a twenty-first root to an already monitored
report succeeds, but monitoring becomes unavailable for capacity. The last valid
checkpoint and retained history remain available under current access checks.

At most 2,000 pending events are retained per inventory monitor. An overflow flag
stops further queue growth. This is separate from the retained-transition limit.
Paused monitors retain pending events within that bound. A capacity or history-gap
message does not mean nothing changed. Explicit recovery is validated by the
server; a fresh baseline acknowledges skipped intermediate differences. An
oversized inventory cannot be recovered by silently selecting only some roots.

History remains accessible from the unavailable monitor page, including exact
comparison export. Each request rechecks current access and retained integrity.
Recovery controls do not bypass those checks. Migration 0031 adds the mode and
overflow state, preserving old monitors as selected-root subscriptions.

Open the monitor to see its status and retained transition history. Each
transition preserves the exact before/after revisions, evidence, frozen assessment
and notification policy. Its link always opens that transition, including from
an alert. JSON export returns the retained comparison with its digest, subject
to current access and integrity checks.

Pause retains pending corrections. Resume with catch-up processes them in order;
resume with a fresh baseline explicitly skips individual pending differences and
records that baseline transition. Changing notification categories or enabling
alerts requires the same explicit fresh-baseline acknowledgement. Renaming alone
does not change the notification policy. Team alerts are visible within the
report's authorised team scope, rather than being personal notifications.

Permanent removal deletes the selected monitor, its retained transitions, queued
observations and alerts. It preserves the report and other monitors. The interface
explains that history removal is irreversible and supports cancellation.

## Persistence and authority

Migration 0030 adds monitor/watch rows, an ID-only revision outbox and immutable
transition manifests. Each successful annotation append queues exact revision and
predecessor IDs for every watcher in the same transaction. Independent monitors
consume their own events, so rapid reversals and multiple subscribers are not
collapsed into a latest-only observation.

The worker uses the shared administration guard, current active owner and current
membership of an active team. A checkpoint CAS, retained transition, optional alert
and event consumption commit together. The worker runs independently of feed
collection, recovers from transient cycle errors and stops before storage closes.

Unavailable authority, corrupt/missing anchors, history gaps or exhausted capacity
preserve the last valid checkpoint. They are not inferred withdrawals or unchanged
observations. Name/date/order-only differences do not produce alerts; rationale,
statement, disposition, citation and substantive conflict corrections remain
meaningful in the selected categories.

Limits are twenty monitors per personal/team scope, one thousand globally,
twenty selected roots per monitor, two thousand retained transitions per monitor,
64 MiB of retained manifests per scope and 256 MiB globally. Current checkpoints
and transition history are both charged. No silent history pruning or automatic
reset is used to evade a limit. Explicit removal allows capacity reclamation.

Alert origins distinguish indicators, research schedules and annotation monitors.
Private snapshots and excerpts stay out of shared SSE. Report/monitor deletion
performs explicit dependent cleanup, including SQLite use with foreign keys off.
Downgrade refuses retained or damaged monitor history instead of discarding it.

## Verification record

- Ten PostgreSQL 17.10 concurrency cases passed in 37.00 seconds, with observed
  lock contention and separate database processes. They cover competing workers,
  both append/baseline orderings, membership revocation, parent/monitor deletion
  and exact export. Disposable resources were verified removed.
- Thirty initial expanded cases passed, including SQLite migration preservation,
  parity, clean downgrade/re-upgrade and retained/damaged-history refusal.
- The later expanded run passed 93 cases, including six HTTP response-order and
  token-expiry regressions. Its one mixed-kind fixture used reversed test dates;
  the corrected mixed case passed separately. Five permission cases also passed,
  giving 99 unique local passes. Test setup repairs used valid email input and
  explicitly marked defensive inconsistent membership state; production
  authorisation rules were unchanged.
- Six PostgreSQL migration cases passed in 15.89 seconds, including schema parity,
  acknowledged old-alert preservation, clean roundtrip and retained/damaged
  history refusal. Disposable resources were verified removed.
- Mypy passed 609 source files; both import contracts and configured Bandit passed.
- Full frontend: 1,003 tests in 193 files, 95.07% statements, 90.09% branches,
  93.52% functions and 96.43% lines. Typecheck, global lint and production build
  passed. A subsequent scope-clarity copy change passed twelve affected tests.
- Independent backend review found one HTTP response-order issue. The repair
  places asynchronous session validation before the final guarded operation and
  checks expiry synchronously afterwards. Source re-review found no remaining
  instance in the changed monitoring/comparison routes; runtime regressions pass.

Actual browser acceptance, operator database migration, live deployment, wider
inventory/cross-version monitoring and independent human evaluation remain open.
Local tests are not evidence of those release gates.

All repository hooks passed, including Gitleaks, Ruff/format, file-length
checks and full frontend lint/type checks. Combined acceptance with registry
routing at `0c91741` passed 3,278 backend tests, with 55 skips and 95.06% coverage,
and 1,009 frontend tests, with 90.11% branch coverage. The production build passed.
Report-wide inventory work is tracked in
[the inventory plan](ANNOTATION_INVENTORY_MONITORING_PLAN.md).

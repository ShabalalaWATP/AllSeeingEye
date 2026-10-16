# KAN-242 alert delivery retention

The production session factory does not enable SQLite foreign keys. An expired
alert was deleted while its email/webhook delivery rows survived, including
destination references, lease state and delivery history. The same valid-parent
cases cascade under PostgreSQL. This was reproduced only in disposable databases;
it is not a claim about an operator's production records.

`SqlWarningStore.prune` now removes outbox rows whose parent alert no longer exists,
after alert expiry and within the existing administration-guarded transaction.
The sweep runs even when no alerts expire, repairing historical SQLite orphans.
It retains every outbox row attached to a surviving alert, regardless of delivery
state or age, so retry state and terminal idempotency records remain intact.

The strict alert cutoff, returned alert count, consumption retention and daily
feedback window are unchanged. No migration, public API or global foreign-key
configuration changes are needed. SQL performs the parent existence check without
loading an unbounded ID list into Python. Large legacy outboxes can lengthen this
existing transaction; scheduled bounded maintenance remains KAN-241's scope.

Alert creation and guarded delivery preparation share the administration lock.
Claim, recovery and completion update existing rows and cannot recreate deleted
records. A claim prepared after pruning is rejected. An already released external
request cannot be recalled; completion after pruning is a no-op, matching existing
PostgreSQL cascade behaviour.

Regression tests cover the exact age boundary, all seven delivery states, live
rows belonging to different owners, historical orphans when zero alerts expire,
repeat calls, rollback after a later cleanup failure, retry continuity, terminal
enqueue idempotency and stale completion. SQLite's normal FK-off construction and
explicit FK-on mode are both exercised. PostgreSQL runs use the existing disposable
database configuration. Existing routing, revocation, feedback and consumption
tests remain the surrounding integration checks.

Independent review found no concrete correctness or security defect. Its suggested
concurrency check was added: a delivery reader pauses before the administration
guard, a separate connection commits pruning, then preparation resumes and must
refuse the deleted alert. Completion cannot recreate the outbox row. The SQLite
case uses a file-backed database, rather than the in-memory single connection.

This repair still runs when the evaluator prunes. It does not claim disabled-feed
cleanup, complete account erasure or removal of delivered messages/backups. See the
[retention schedule](../compliance/RETENTION_SCHEDULE.md) and
[delivery queue](../delivery/CODEX_QUEUE_2026_10_16.md).

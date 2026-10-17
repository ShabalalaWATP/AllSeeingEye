# Retention when workloads are idle

KAN-241 enforces existing expiry rules without waiting for another feed event,
selected-source page, AI call, research request or push delivery. The application
starts the housekeeping worker even when feeds and optional delivery providers
are disabled. It never enables those providers or sends a message. Deployment
of this change starts the worker; code review is not evidence of a live purge.

## What expires

| Records | Eligibility and safeguards |
| --- | --- |
| Selected public metadata | Reads exclude `expires_at <= now` and records first seen at least 400 days ago before sorting/limiting. Background removal uses the same cutoffs, including paused/archived subscriptions and deactivated owners. Acquisition cursors and page hashes remain. |
| Selected corrections and coverage | Expiry detaches bounded correction links, preserving their fingerprints. Parents with remaining references wait for another rotation. Actual removals increment coalesced age-loss summaries in the same transaction. |
| Alerts and feedback | Alerts strictly older than 30 days expire. Outbox children of expired or missing parents drain before parents, including legacy SQLite orphans. Current alerts retain their delivery/retry records. Feedback uses the existing daily-bucket boundary. |
| Consumed warning identities | A digest expires strictly before the current instant, preserving the inclusive seven-day eligibility edge. Mixed-age rows retain live identities. Corrupt rows remain fail-closed, and do not prevent later rules from being scanned. |
| Push receipts | Receipts strictly older than seven days expire unless a current sending lease or an alert within the inclusive one-day delivery horizon still needs them. Device registrations and credentials remain. |
| Research allowances | Obsolete UTC day and Monday-based week buckets expire. Current and future buckets and tier assignments remain. Admission and cleanup use the existing administration/account lock order. |
| AI allowances | Existing pruning removes finished reservations strictly past 90 days and unheld counters/totals strictly past 400 days. Reserved/unknown calls and held counters remain. The worker does not reconcile or settle uncertain calls. |
| Private input slots | The bounded in-memory store releases pending and completed slots at their existing expiry, including derived inputs whose parent expires sooner. Unexpired inputs remain. Selected content already frozen into a report or checkpoint has its separate lifecycle. |

These rules do not expand raw-event or private-input persistence. No new schema,
provider setting or public API is introduced. The internal selected-record read
method now requires an explicit clock instant so callers cannot omit expiry.

## Batches, time and outages

Each cycle scans at most 100 selected rows and 100 warning rules, detaches at most
100 correction links, and changes at most 100 rows in each other SQL category.
Each AI table has its own 100-row limit. Selected losses are coalesced by source
and subscription. The memory store is already capped at 24 slots.

Selected metadata and warning rules use a fixed primary-key endpoint for each
rotation. Continuing arrivals cannot indefinitely postpone earlier records.
Scan positions advance only after commit. Restart starts a new rotation; repeated
restarts or outages can delay deletion. Selected correction fan-out can require
several rotations. Bounded rows do not imply constant query time: correction
reference checks have no dedicated index, and other predicates may scan indexes
or tables to find a batch.

Each category has its own timer and sleeps 60 seconds after its cycle. Each SQL
category has a 30-second deadline and its own transaction; a stalled category
does not delay memory expiry or another category's heartbeat. The normal interval
is cycle duration plus 60 seconds, with cancellation/rollback scheduling potentially
adding delay. This is not a hard wall-clock service guarantee. Backlogs can take
multiple cycles/rotations. Shutdown joins every category before closing the database.
Selected-metadata reads and private-input access enforce expiry immediately, even before physical
cleanup. There is no claim of secure memory wiping or removal of external copies.

## Operations and holds

Worker health names are `retention_private_inputs`, `retention_selected`,
`retention_consumed`, `retention_alerts`, `retention_push`, `retention_research`
and `retention_ai`. Category failures log the category only, without driver
messages, record content or connection details. Investigate repeated failures
using authorised local diagnostics. A missing selected-index gate fails closed;
use the supported migration procedure rather than inserting production rows.

The optional KAN-238 authentication and KAN-239 audit/per-call/delivery policies
retain their own enable/pause/hold controls. Those controls do not pause these
pre-existing expiry rules. A broader preservation requirement needs an operator
plan covering every writer and external copy. Stopping this worker alone would
not stop opportunistic expiry in existing admission/evaluation paths.

Release approval must account for automatic cleanup of an existing backlog when
the new version starts. Use the normal backup, migration and release procedures;
do not run ad-hoc production SQL. Review continuing retention at least quarterly,
as recorded in the [retention schedule](compliance/RETENTION_SCHEDULE.md).

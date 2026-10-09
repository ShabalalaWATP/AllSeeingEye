# KAN-217: durable alert report admission

The previous indicator evaluator awaited report generation inside each rule's
routing step. A slow model call therefore delayed the remaining rules and the next
evaluation cycle. The regression test initially failed at the barrier asserting
that evaluation had completed while reporting was blocked.

## Behaviour and recovery

- An alert stores a pending report intent in its existing persistence transaction.
  The evaluator performs no report preparation or model calls.
- A separate lifecycle-managed admission runner handles a bounded page of eight
  intents per minute. Each preparation has a 30-second deadline. Capacity is retried
  after five minutes, and pending intents expire after 24 hours.
  Due requests are ordered by next-attempt time so deferred capacity failures yield
  to untouched requests. The existing rounded-hour report interval ends at the
  alert's firing time, including after a delayed admission. The exclusive upper
  bound is one microsecond later to retain evidence exactly at the firing instant,
  matching the evaluator's inclusive boundary at Python datetime precision.
- Admission reuses `ReportJobService`, its allowance controls and a stable request
  key derived from the alert ID. Job creation and the alert link commit together.
  Concurrent preparation, process restart and lost commit acknowledgement cannot
  produce another automatically submitted job for the alert.
- Execution uses the existing bounded report workers, checkpoints and paid call
  ledger. Interrupted or failed paid work is visible through the alert and the
  existing progress page, without automatic resume.
- Admission, worker checks and final publication require the original rule revision
  and current owner/team authority. Final report persistence and alert attachment
  commit together. Outcome reads exclude mismatched job ownership or team links.
- The warning UI displays the durable outcome and polls through the existing
  visibility-aware scoped resource hook.

## Migration and rollout

Migration 0090 is additive and has no historical replay or status backfill. A unique
nullable job link prevents two alerts sharing one report job. Deleting retained job
progress clears the foreign key and displays discarded progress on the alert,
without returning the intent to pending. Normal application rollback should retain
the added fields. Downgrade refuses to discard non-null alert report history.

The migration was exercised on a disposable SQLite database, including upgrade,
historical alert preservation, foreign-key/uniqueness metadata and guarded downgrade.
PostgreSQL and production rollout were not exercised locally. Apply migrations
before the application starts, using the existing release process.

## Verification scope

Deterministic tests cover blocked/failing provider work while later rules and cycles
continue, durable success, explicit failure, expired leases without replay,
simultaneous admission, shutdown during preparation, capacity deferral, stale rule
revisions, team membership removal and owner revocation during provider work.
Existing report-job, warning route and application lifecycle tests exercise the
affected integration paths. Frontend warning tests cover visible progress links and
admission errors. Final command results are recorded in the implementation handoff.

Local results (9 October 2026): the broader affected backend group passed 68 tests;
after review repairs the final queue, fence, fairness and route group passed all
22 tests. The warning frontend group passed 68 tests in 15 files. Ruff check and
format checks, strict mypy (1,592 source files), all three import contracts, Bandit,
frontend changed-file ESLint, frontend type checking and production build passed.
OpenAPI and TypeScript API declarations were regenerated. Coverage was not measured
in these focused runs; the full coverage and integration gates remain with CI.
The build retained existing large-chunk advisory messages. Bandit reported existing
unmatched suppression comments in the Chromium adapter, with no findings.

Independent review identified and resolved admission starvation under repeated
capacity refusal and interval drift during delayed admission. Deterministic tests
cover a later eligible owner progressing beyond 40 deferred intents, and a two-hour
capacity delay preserving the original interval.

KAN-218 report scope, KAN-219 template validation and KAN-220 evidence deduplication
remain separate changes. This change deliberately preserves the existing report
request scope contract. No network provider calls or production services were used.

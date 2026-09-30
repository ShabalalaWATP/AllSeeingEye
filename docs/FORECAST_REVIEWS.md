# Forecast reviews and outcome counts

The report reader's **Forecasts and review history** panel starts from an exact
reviewed claim revision. A forecast freezes its supporting and contrary passages,
resolution criterion, original PHIA band, confidence dimensions, review date and
outcome horizon. These annotations never rewrite the report body, its grades or
its confidence. There is no provider request in this workflow.

## Reviews and replacements

An unresolved review is permitted after the outcome horizon. A resolved review
requires an explicit true or false outcome and a reviewer reason. It also requires
at least one exact reviewed claim passage from a report version frozen after the
forecast was issued, in the same personal or team scope. The passage must have a
known published or observed time after issue and no later than review. The report
link, exact report version and reviewed passage are selected in the review form.
The server rechecks all report, claim, revision and excerpt identities.

This is a human judgement based on retained evidence. It does not infer a resolved
outcome from a free-text reason, an unresolved row, a missing feed or a PHIA band.
Quantitative source verification remains separate from this reviewer workflow.

Reviews carry the expected forecast version and prior decision. Final decisions
can only change through a linked, append-only reviewer correction. Replacing an
open forecast atomically records a superseded decision and its new version. A
replacement retains the ledger's original exact reviewed claim anchor. The old
band, dates, confidence and evidence stay in history. Concurrent or stale writes
return a conflict. Legacy reviews without a version token work only for the first
version; they cannot accidentally review a replacement.

## Review reminders and Watches

The Alerts page contains **Forecast watches and outcome counts**, scoped to
Personal or a selected accessible team. Review due means the current version's
`review_at` has passed while its outcome remains open or due. Outcome state `due`
continues to mean its separate `horizon_end` has passed. Neither state resolves a
forecast automatically.

Opening Watches records at most one in-app reminder receipt per forecast version
and review date. The receipt is shared by authorised readers of a team forecast.
Reads and writes use the existing administration lock and session release fence.
Archived teams remain readable but cannot acquire reminder receipts. Ordinary
members cannot change their forecasts; the existing administrator write override
is preserved. Leaving a team removes access to its watches, exports and
counts. Reminder receipts disappear when their parent report is deleted.

Opt-in email delivery is owned by the notification pipeline. Its read-only
`forecast_digest.due_review_count` projection returns current versions scheduled
in the requested half-open review-date interval, with an explicit truncation flag
above 1,000 accessible ledgers. It uses current active team membership, excludes
final outcomes and never expands a recipient's scope using administrator rights.
The notification pipeline must call it under its current-access delivery lock.
In-app review operates independently of email configuration.

## Counts and exports

Counts select scope before aggregation, then use the chosen UTC issue-time cohort
`since <= issued_at < until`. Each forecast version contributes once, under its
frozen original band and latest valid decision. A correction replaces the counted
outcome, without adding an observation. True and false alone form the resolved
denominator. Superseded, unresolved, open and horizon-due counts remain separate.

Related versions may not be independent observations, and a cohort may be small
or selective. PHIA bands are not calibrated probabilities. The UI shows counts
and denominators, with explicit empty, unresolved, loading, error and lost-access
states. It computes no observed percentages, midpoints, Brier score or accuracy
estimate. Cohorts above 1,000 accessible ledgers fail explicitly instead of showing
incomplete totals; select a narrower workspace.

Select individual forecast histories to download a separate JSON export. This
operation rechecks the current session and exact report version and only includes
the selected ledgers. Ordinary report exports are unchanged. It is not a frozen
report-body revision.

## Storage and verification

Migration `0073` adds the composite-key reminder receipt table. Its standalone
branch predecessor is `0070`; grouped integration must preserve the single
migration chain. Forecast versions and decisions reuse the retained ledger tables
and integrity codec. Supersession appends two entries with one optimistic ordinal
update in the same transaction.

Focused synthetic tests exercise evidence provenance, foreign scopes, corrections,
supersession, clock boundaries, reminder deduplication, archived and departed team
members, exports and displayed outcome counts. SQLite migration execution and
offline PostgreSQL DDL are distinct from a live PostgreSQL concurrency run. Live
provider, mail delivery, production data and calibration claims are out of scope
for these deterministic checks.

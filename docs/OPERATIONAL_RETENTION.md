# Audit, usage and delivery retention

KAN-239 provides an optional independent worker and `ase operational-retention`.
It does not require feeds, mail configuration or new activity. Automatic maintenance
is **off by default**. Code availability does not establish production erasure.
Review the counts-only preview and approve the installation policy before rollout.

## Purpose and periods

These proposed defaults are operational choices, not statutory requirements.
Alex Orr owns the installation decision; approving this PR adopts the documented
defaults in code, while enabling maintenance or purging production remains separate.

| Category | Default and purpose | Action strictly after the cutoff |
| --- | --- | --- |
| `audit` | 365 days from event time, supporting security investigation across an annual cycle | Delete the complete event, including actor, IP, subject and details. |
| `llm_usage` | 400 days from call time, supporting annual usage reconciliation with a short buffer | Delete the complete per-call receipt. Always retain the current UTC accounting month. |
| `subscription_email` | 90 days since last recorded delivery activity, supporting delivery troubleshooting | Clear recipient reference, lease, retry date and reason on terminal email receipts. |
| `digest` | Same 90-day inactivity window | Clear lease, retry date and reason on terminal daily receipts. |

Each window is configurable from 30 to 3650 days through `ASE_AUDIT_RETENTION_DAYS`,
`ASE_LLM_USAGE_RETENTION_DAYS` and `ASE_DELIVERY_HISTORY_RETENTION_DAYS`.
An exact cutoff is retained. A delivery's `updated_at` records delivery activity;
some opt-out transitions do not update it. Consequently, cancelling a long-idle
intent can make it eligible immediately. This is not a promise of ninety days
after cancellation. Minimisation never changes historical timestamps or attempts.

Subscription terminal states are `sent`, `failed`, `cancelled` and `uncertain`;
digests also include `empty`. Preserve `pending`, `sending`, `unavailable`, unknown
states and every non-email subscription channel. Old retryable work remains usable.
Out-of-date delivery leases are recovered by their existing workers, not by this job.

## Records deliberately retained

Subscription receipt identity, unique key, edition, event, channel, outcome, attempts
and timestamps remain. A known edition/user pair can reproduce its deterministic
key, so clearing the recipient reference is minimisation, **not anonymisation**.
Digest user/local-day identity, original timezone and UTC interval remain to prevent
repeated daily messages and preserve truthful historical boundaries. Never rewrite
the timezone to UTC or delete uncertain receipts to make a count smaller.

These compact receipts remain while their parent work/account remains. Review their
continuing need quarterly and at closure. Dependency-aware account and saved-work
removal is KAN-240; this command does not provide complete erasure. Preferences,
opt-outs, in-app events, account details, job checkpoints, monthly projections and
AI allowance reservations/counters/totals remain unchanged. KAN-241 covers separate
dormant allowance maintenance. Backups, exports and provider/mailbox copies are
outside this command and remain in the [retention schedule](compliance/RETENTION_SCHEDULE.md).

## Holds and rollout

1. Record the selected database, operator, purposes, approved windows, outstanding
   rights/security cases and review date in a restricted operations record.
2. During an investigation, set `ASE_OPERATIONAL_RETENTION_PAUSED=true`, or hold
   whole categories with a JSON array, for example
   `ASE_OPERATIONAL_RETENTION_HELD_CATEGORIES='["audit","llm_usage"]'`.
   Only the four names above are valid. Invalid settings fail closed.
3. Apply configuration to **every** API/maintenance process and stop/restart them
   cleanly. Holds are process configuration, not dynamically refreshed database
   flags. A transaction already committed cannot be recalled. A category hold
   conservatively protects all its records, including evidence identifying a person
   in another actor's subject/details. Record reason, custodian and next review date
   privately. There is no per-person or reusable integer-ID hold claim.
4. Run `uv run ase operational-retention` from the configured backend directory.
   Output contains mode, pause, held categories and eligible next-batch counts only.
   Zero for a held category means no permitted action, not proof of no older records.
5. After separately authorising production erasure, `--apply` executes one batch.
   Alternatively set `ASE_OPERATIONAL_RETENTION_ENABLED=true` and restart to run
   every minute. Re-preview to observe progress. No migration is required.

Each transaction changes at most 100 rows per category (400 total); repeated
transactions make progress and skip already minimised receipts. The preview does
not lock records and is not an exact future execution plan. Apply takes the existing
administration guard, checks predicates again and commits all categories together.
This bounds changed rows, not scan time: a large unindexed historical backlog may
need a quiet maintenance window. Failure logs omit exception/row content; inspect
counts and the selected database before retrying. The CLI never creates or migrates
schema. SQLite integer history IDs may be reused after deletion, so they are not
permanent cross-archive identifiers.

These holds cover this worker and CLI only. Ordinary user deletion, account changes,
other housekeeping and external copies have separate behaviour. For a wider legal
hold, restrict those actions and preserve necessary evidence under an explicit
operator plan. Do not describe this switch as a universal forensic freeze.

## Review evidence

Alex Orr reviews necessity at least quarterly, next due **14 January 2027**, and
on purpose completion, a rights request, an incident or closure. Until rollout is
verified, retain the existing manual review duty. Afterwards continue reviewing
windows, holds and compact receipts. Record policy version/commit, actual deployed
revision, selected periods, enable/pause state, preview/applied category counts,
failures, hold rationale and next review date privately. Keep record contents and
credentials out of logs, Jira and public documentation. No production cleanup or
live deployment is claimed by the local test evidence.

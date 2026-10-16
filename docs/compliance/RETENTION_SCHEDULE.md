# Retention and deletion schedule

Reviewed **14 October 2026** against `14a65442`; owner **Alex Orr**. The
[record index](README.md) distinguishes defaults from the dated live observation.
Periods below are source defaults/constants unless stated otherwise. A token's
expiry, read exclusion, content scrubbing and physical row deletion are different
events. Housekeeping needs a running installation and can lag during outages or
batch backlogs. No universal statutory deletion period is asserted.

Code follow-up, **16 October 2026**: KAN-238 and KAN-239 add optional maintenance
for the categories identified below. Both remain off by default. Their presence
does not update the dated live observation or establish production rollout. KAN-241
adds independent housekeeping for existing expiry rules, active when the application
starts; its [guide](../DORMANT_RETENTION.md) distinguishes immediate access expiry,
bounded sweep backlogs and optional-policy holds. Release approval remains required.

The approved notice requires necessity review **at least quarterly**, plus review
on account closure, purpose completion and rights requests. Next scheduled duty:
**14 January 2027**. This is a manual commitment, not an automatic deletion job or
reminder. Record category, purpose, continuing reason/hold, access restriction,
action and next review date privately. Use supported controls; do not improvise
cross-table production SQL or claim complete erasure where tooling is absent.

## Authentication and operational records

| ID / records                                | Current rule and actual trigger                                                                                                                                                                                                       | Limitation / follow-up                                                                                                                                                                                              |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T01: accounts, profiles and team membership | Retained until supported changes/removal. Deactivation revokes access, sessions and matching push registrations but retains identity/profile/history.                                                                                 | Review quarterly and on closure, with shared ownership/last-manager safeguards. KAN-240 adds explicit [private-data review/removal](../PRIVATE_DATA_REMOVAL.md), preserving a permanently inactive identity stub, shared history and audit. No live removal or general anonymisation is implied.                                                    |
| T02: access requests | Optional KAN-238 maintenance erases approved/rejected requests at least 90 days after decision (configurable 30 to 3650), at most 100 per minute. Pending/unknown/undated requests remain. | Off by default; review the counts-only CLI preview and authorise rollout. A global housekeeping pause preserves this category. See [authentication retention](../AUTH_RETENTION.md). |
| T03: sessions and password links | Runtime lifetimes remain access 15 minutes, idle 180 minutes, refresh 14 days, activation 7 days and reset 30 minutes. Optional housekeeping erases links seven days after use/expiry and refresh tokens only when the whole family expired at least 91 days ago. | All ancestors remain while a newer descendant is within the retention window. Push dependencies drain in bounded batches first; activity/revocation records wait until tokens/devices are gone. Opportunistic unbounded logout pruning is removed. Rollout remains separate. |
| T04: MFA | Runtime challenge 10 minutes, emailed code five minutes and pending TOTP 10 minutes. Optional housekeeping deletes expired/consumed challenges and clears expired pending TOTP material. | Confirmed factors, replay-protection state, email MFA and recovery codes are preserved. The global auth-housekeeping pause applies; normal security revocation/removal remains active. |
| T05: audit | Optional KAN-239 maintenance deletes complete events strictly older than 365 days (configurable 30 to 3650), at most 100 per minute. | Off by default. Category/global holds preserve evidence. Review proposed purpose-based periods, preview and separately approve rollout; see [operational retention](../OPERATIONAL_RETENTION.md). |
| T06: research allowance counters | Existing admission pruning plus independent batches of 100 obsolete UTC day/week buckets per cycle. | Current/future buckets and tier assignments remain, including for dormant accounts. See [dormant retention](../DORMANT_RETENTION.md). |
| T07: AI allowance and usage | Finished reservations: 90 days after period end. Unheld counters/totals: 400 days after period end, now also independent batches of 100 per table per cycle. Optional KAN-239 per-call expiry remains strictly older than 400 days, protecting the current UTC month. | Held/unknown reservations and held counters remain; independent expiry does not reconcile calls. Per-call maintenance stays off by default with separate category/global holds. |

Evidence: [user deactivation](../../backend/src/ase/application/admin/users.py),
[request decisions](../../backend/src/ase/application/admin/requests.py),
[settings](../../backend/src/ase/infrastructure/settings.py),
[link lifetimes](../../backend/src/ase/domain/tokens.py),
[bounded authentication cleanup](../../backend/src/ase/adapters/persistence/auth_retention.py),
[MFA](../../backend/src/ase/application/auth/mfa.py),
[audit](../../backend/src/ase/adapters/persistence/audit.py),
[research counters](../../backend/src/ase/adapters/persistence/research_usage.py),
[AI maintenance](../../backend/src/ase/application/ai_usage.py) and
[per-call usage](../../backend/src/ase/adapters/persistence/llm.py).

## Notifications and retained research

| ID / records                                      | Current rule and actual trigger                                                                                                                                                                                         | Limitation / follow-up                                                                                                                                                                                                           |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T08: alerts and consumed-evidence digests | Alerts strictly older than 30 days and corresponding feedback buckets expire independently of feeds. Consumed identities retain the inclusive seven-day eligibility edge. | Batches of 100; outbox children drain before parents. Fixed-endpoint warning-rule scans preserve live digests and corrupt fail-closed state. Sweep backlogs can delay physical removal. |
| T09: delivery history | Alert email/webhook rows cascade on alert deletion with enforced foreign keys; KAN-242 separately addresses SQLite orphan cleanup. Optional KAN-239 minimises terminal subscription/digest receipts strictly after 90 days of recorded delivery inactivity, at most 100 per category per minute. | Off by default; category/global holds apply. Duplicate-prevention keys and digest day/user/window remain; this is minimisation, not anonymisation. Pending/sending/unavailable records and opt-outs are preserved. Review retained receipts quarterly and on closure, with KAN-240 for dependency-aware removal. |
| T10: push registration and receipts | Security/device removal retains its existing behaviour. Receipts strictly older than seven days now expire even with push unconfigured, in batches of 100. | Current sending leases and the inclusive one-day alert delivery horizon are preserved. Credentials and browser vendor copies have separate lifecycles. |
| T11: reports, frozen evidence and job checkpoints | Authorised report deletion removes linked versions/evidence/claims/ledgers/originals/maps/library/embeddings. Inactive job checkpoints have a separate explicit discard after reservation checks; final reports remain. | No age purge. Checkpoints can independently hold selected private evidence. Review purpose completion/quarterly; KAN-240 provides preview-bound private removal, including inactive settled checkpoints, originals and search projections; retained references block deletion. Audit/backups remain separate.                                       |
| T12: briefs and subscriptions                     | Archive disables a schedule but retains revisions, editions, comparisons and lineage. Referenced reports remain deletion-blocked even after archive. Brief revisions persist separately.                                | Archive is not erasure. Review continuing/shared need; KAN-240 can remove an archived private graph after a recorded necessity decision, with active/uncertain work, shared authorship and retained references blocking removal.                                                                                       |
| T13: selected subscription metadata | Reads exclude stored expiry and the maximum 400-day age before sorting/limits. Independent fixed-endpoint scans remove at most 100 rows per cycle, including paused/archived subscriptions and deactivated owners. | Preserve cursor/page hashes, correction fingerprints and coalesced coverage-loss records. Large correction fan-out requires later rotations; physical deletion may lag read exclusion. Public metadata only. |

Persistent notification choices and credentials (**T20**) have a separate lifecycle:
explicit private Atom-feed revocation deletes its token-hash row; security-version
invalidation only prevents use. Email opt-out cancels intents and changes preferences,
but retains preference rows. Webhook removal disables the destination and detaches
routes while retaining the encrypted URL. There is no general age purge for these
records. KAN-240 explicitly removes selected private feed hashes, email/digest
settings and disabled personal webhook credentials. Surviving shared dependencies
block removal. Review unused destinations and preferences quarterly and on closure.

Evidence: [feed-token revoke](../../backend/src/ase/adapters/persistence/notification_feed.py),
[private-feed access](../../backend/src/ase/application/account/private_feed.py),
[destination removal](../../backend/src/ase/adapters/persistence/alert_routing.py) and
[preferences](../../backend/src/ase/adapters/persistence/notification_preferences.py).

Evidence: [alert prune](../../backend/src/ase/adapters/persistence/warning_store.py),
[evaluator startup](../../backend/src/ase/app_lifecycle.py),
[outbox foreign key](../../backend/src/ase/adapters/persistence/alert_routing_models.py),
[SQLite sessions](../../backend/src/ase/adapters/persistence/session.py),
[push worker](../../backend/src/ase/container/web_push.py),
[report deletion](../../backend/src/ase/adapters/persistence/reports.py),
[job discard](../../backend/src/ase/application/report_jobs/controls.py),
[report dependencies](../../backend/src/ase/adapters/persistence/report_links.py),
[schedule archive](../../backend/src/ase/adapters/persistence/schedules.py) and
[selected-index expiry](../../backend/src/ase/adapters/persistence/selected_index_eviction.py).

## Inputs, enquiries and copies

| ID / records                                                 | Current rule and actual trigger                                                                                                                                                                                                                                                                                       | Limitation / follow-up                                                                                                                                                                                          |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T14: private input receipts | 15-minute process-local access. Existing activity-based expiry plus independent housekeeping releases expired pending/complete slots, preserving earlier parent-derived expiry. Discard and process-exit rules remain. | The store is capped at 24 slots. Its independent timer runs every cycle plus 60 seconds without waiting for SQL categories; outages/backlogs can still delay removal, while access expiry remains immediate. Frozen job/report evidence follows T11. |
| T15: originals and fetched passages                          | Explicit assets: selected 1-90 days, default 30. Expiry/deletion scrubs bytes and identifying fields; lifecycle rows are removed 30 days after transition. Fetched passages have separate policy, default one day, maximum 30, and are physically deleted on expiry. Minute housekeeping runs independently of feeds. | Saved report extracts and recovery copies remain separate. Selected asset periods do not remove those copies; necessity/removal follows T11/T18.                                                                |
| T16: enterprise enquiries                                    | Default 365 days from submission, configurable 30-3650. Reads exclude older records; minute sweep deletes up to 100 even when new submissions are disabled. Authorised manual deletion exists. Exact cutoff is retained; status changes do not reset age.                                                             | Outage/backlog can delay physical deletion. Mailbox/backup copies are separate. Delivered under KAN-167; runtime period should be verified on the deployed release before asserting its effective value.        |
| T17: public live data and snapshot                           | Bounded category age/count budgets; normal 60-second feed pruning. Examples: aviation/satellite positions 10 minutes, vessels 15 minutes, conflict/cyber up to 30 days. Snapshot defaults: 300-second replacement, 128 MiB cap, final shutdown save, retention reapplied on restore.                                  | Snapshot is disposable public cache and excluded from backup. An offline/disabled installation can retain an old file; these windows are not disk-erasure deadlines. KAN-243 covers offline-file review.        |
| T18: backups, releases and logs                              | Scheduled helper keeps newest 30 archives, minimum three, after successful verification; operator scheduling is required. Release pruning separately defaults to five releases, minimum two, dry-run until `--apply`. Compose logs rotate at five files of `20m` per container.                                       | Counts/sizes are not ages. Manual and remote copies are outside scheduled pruning. No automatic replay of later erasure/deactivation on restore. [KAN-243](https://alex-orr.atlassian.net/browse/KAN-243).      |
| T19: mailbox, provider, archive, browser and exported copies | Review correspondence on resolution and quarterly. Browser storage follows the [inventory](../../frontend/src/features/public-policy/storage.json) and user controls. Provider copies follow their terms; recipient downloads/public archives remain separately controlled.                                           | No universal application purge. KAN-243 records external-copy review and request handling; KAN-185 reviews recipient arrangements. Deleting a local record cannot recall a delivered message or public archive. |

Evidence: [receipt store](../../backend/src/ase/adapters/research_inputs/memory.py),
[asset cleanup](../../backend/src/ase/adapters/persistence/original_assets.py),
[asset/housekeeping loop](../../backend/src/ase/container/original_asset_expiry.py),
[passage policy](../../backend/src/ase/application/research/original_policy.py),
[enquiry deletion](../../backend/src/ase/adapters/persistence/admin_enquiries.py),
[live budgets](../../backend/src/ase/application/feeds/budgets.py),
[snapshot](../../backend/src/ase/application/feeds/live_snapshot.py),
[scheduled archives](../../scripts/scheduled_backup.py),
[release pruning](../../scripts/prune_deployments.py) and
[log rotation](../../docker-compose.yml).

## Review and recovery procedure

The 11 October observation recorded a daily backup and weekly archive verification
drill using default count retention and no off-site override. It does not establish
today's schedule, a fixed maximum age, or successful full recovery.

At each review, inventory live records and separately retained copies, record
necessity/holds and use [supported deletion controls](../PERSONAL_DATA_OPERATIONS.md).
Restrict unresolved material and record why it remains plus the next action/date.
Before restoring service from older data, reconcile subsequent deactivations,
deletions, objections, opt-outs and access changes. Inspect remote destinations,
manual exports and mailbox copies separately. KAN-243 adds a protected external
journal, explicit copy-policy/review records and a
[manual pre-reactivation checklist](../RECOVERY_RECONCILIATION.md). Its disposable
SQLite drill restores an older snapshot and reapplies later guarded decisions;
it is not a live or PostgreSQL recovery claim. The journal does not automatically
capture UI changes, prune copies, lift holds or authorise activation. Quarterly
and request-resolution reviews record actual selected periods/counts or holds;
unselected installation values remain open operator actions, not legal deadlines.

The six follow-ups above were created after duplicate review. They preserve the
distinction between a recorded schedule and implemented deletion. Their completion
requires tests and an authorised rollout before the installation can claim the
new behaviour; KAN-187 completion alone does not close them.

KAN-238 implementation review, 16 October 2026: T02-T04 now describe the optional
bounded policy and its explicit preview/apply/enable controls. These are purpose-based
operational periods, not statutory requirements or verified live settings. Automatic
authentication erasure stays off by default; the existing quarterly duty continues
until an authorised rollout establishes effective housekeeping.

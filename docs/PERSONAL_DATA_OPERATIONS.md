# Personal-data requests: current capabilities and proposed procedure

Status, 2 October 2026: capability inventory and selected record-level procedures
reviewed for KAN-23. The proposed operator-assisted policy below awaits the
installation operator's confirmation. There is no account-wide export bundle or
complete account-erasure action. Account deactivation revokes access; it does not
erase all data.

## Responsibility and scope

Proposed contact: the installation administrator through the installation's
existing private support channel. Verify the requester's identity and exact
account before selecting records. Do not publish personal data in GitHub or Jira.

Proposed team policy: preserve shared team work and resolve responsibility with
the team before changing membership. A person's authorship does not make all
team records personal exports or authorise deleting shared work. The operator
must choose the route, responsible private contact and shared-team policy; no
legal retention period is inferred here. These choices remain pending.

## Current inventory

| Data | Supported behaviour | Retained data or limitation |
| --- | --- | --- |
| Account identity, directory profile, avatar, preferences | Read own profile; edit supported fields; replace/remove avatar using account controls | No combined personal-data export or full identity erasure |
| Personal reports and versions | Export each authorised saved version as Markdown/PDF/DOCX; delete an individually selected personal report | Deletion removes linked versions, evidence, claims/ledgers, passages/originals, map views, library entries and embeddings; audit and backups remain |
| Briefs, collection plans, schedules and subscriptions | Existing scoped readers and supported edit/archive/pause controls | No unified account export; subscription archive retains editions/history rather than erasing them |
| Transient private inputs | Expire under the input-receipt lifetime (15 minutes) and process lifetime | Selected saved evidence and explicitly retained originals are separate; expiry of a receipt does not erase a report |
| Selected original assets | Per-report scoped access and existing retention/deletion rules | Backups or already downloaded copies are separate; no account-wide bulk erasure action |
| Notes, saved maps/chats, annotations and team-board contributions | Existing scoped readers and per-feature supported controls | No unified export/removal operation; inventory each feature and ownership before promising completeness |
| Team contributions/memberships | Read by current members/admin; supported promotion, transfer of leadership and removal | Shared records remain team-owned; removal/deactivation does not erase prior contributions |
| Password hashes, encrypted factors/provider secrets, sessions and links | Deactivation revokes sessions and links; factor/provider management has explicit controls | Do not include credentials or secret-bearing configuration in an ordinary user export; deactivation retains stored records |
| Account/subscription email and daily-digest preferences | Read/change own settings, subscription choices, digest time zone/hour; disable email or digest | Opt-out cancels the corresponding email/digest intents or marks sending attempts uncertain; preferences and delivery history are not erased. It does not disable the separate installation-wide webhook copy |
| Private Atom-feed token and title preference | Replace the token or explicitly revoke the feed; revocation deletes the account's token-hash row | Raw token is shown once, stored only as a hash and excluded from ordinary exports. Deactivation/security-version changes invalidate access without promising row deletion; browser sign-out alone does not revoke it |
| Browser-push devices and endpoint credentials | List own device metadata; remove an owned device. Session/account security invalidation removes matching registrations and receipts | Stored endpoint, p256dh and auth credentials are encrypted and not returned by device listing. Local removal cannot recall vendor/browser copies; browser unsubscribe is best effort when offline |
| Per-rule routing and webhook destinations | Existing scoped controls configure routes and disable destinations | Removing a destination disables it but retains its encrypted URL. Shared-team destinations, route rows and delivery records need ownership review; disablement is not credential erasure |
| Installation-wide webhook copy | The operator-controlled `ASE_ALERT_WEBHOOK_URL` setting can copy every personal/team indicator firing, subject to current owner/scope authority | Account opt-outs and per-rule choices do not disable this separate copy. Inventory its configured recipient and retained copies separately; this procedure does not change the installation setting |
| Notification delivery records | Corresponding preferences and current authority are checked at the final pre-send boundary; push-device removal also deletes its receipts | A released network attempt cannot be recalled. Subscription, digest and alert-routing outboxes retain IDs, attempts and outcome metadata; digest records include interval/time-zone metadata. Push workers prune receipts older than seven days, not according to a stated legal retention policy |
| Audit and usage/allowance records | Administrators can inspect existing audit/usage views | No documented per-account erasure/retention schedule; security and accounting records can survive deletion of content |
| Backups and external copies | Follow the operator's approved backup/restore process and explain channel-specific copies | Live deletion cannot remove old archives, downloads, feed-reader copies or accepted email/push/webhook deliveries |

Source boundaries: [report deletion](../backend/src/ase/adapters/persistence/reports.py),
[account administration](../backend/src/ase/application/admin/users.py),
[transient input storage](../backend/src/ase/adapters/research_inputs/memory.py),
[original asset records](../backend/src/ase/adapters/persistence/original_asset_models.py)
and [team authority](api/TEAMS_API.md). Notification controls and their delivery
limits are described in [email/private feeds](NOTIFICATIONS.md),
[per-rule routing](ALERT_ROUTING.md) and [browser push](WEB_PUSH.md). Each product's
API remains authoritative for the individual action; this inventory is not an
account-erasure implementation.

## Supported record-level rehearsal

Use a disposable seeded installation before applying any approved destructive
request. Never point a development rehearsal at an operator database.

1. Verify the requester/account and agree the exact personal record IDs and
   saved versions. List all pages of visible reports, then select only personal
   records belonging to that account. Visible team work is not a personal bundle.
2. Export those exact versions through existing report export controls. Check
   the resulting files against the agreed list; exclude other users' personal
   records and team-only records. Transfer privately through the agreed channel.
3. Review standing work and disable/pause/archive the relevant schedules or
   subscriptions using their supported controls. Archiving retains history.
   Deactivation also prevents work requiring a current active owner.
4. For an approved record-deletion request, delete only the agreed personal
   reports through their supported API/UI. Confirm removed report/version
   counts and unchanged team/other-user counts. Do not issue ad hoc SQL.
5. If deactivation is requested, appoint another active manager wherever this
   account is the only active manager of an active team, or agree to archive
   the team. Then use administrator deactivation. Confirm old sessions fail
   and another authorised member can still read shared team work.
6. Record what was exported, removed, deactivated and retained using identifiers
   and counts rather than copied content. Explain backup copies and external
   provider copies separately; follow their approved policies.

This procedure handles selected supported actions. It cannot truthfully certify
a complete account-wide export or erasure. Where notification records are part
of a request, inventory them separately using the linked channel guides; the
selected rehearsal below does not prove their complete removal.
In particular, user preference changes do not stop the operator-controlled
installation-wide webhook copy or recall a delivery already released to a channel.

## Unsupported account-wide work

An account-wide bundle or erasure needs separately scoped implementation and
policy decisions. The concrete follow-up boundaries are:

- **Inventory and export bundle:** enumerate personal records, all pages and
  exact saved versions, including notification settings and non-secret delivery
  metadata. Acceptance must exclude other accounts, team-only work and credentials,
  declare omissions in a manifest and recheck current authority before release.
- **Account removal:** decide the treatment of identity, audit/usage history,
  notification/routing metadata and encrypted credentials before implementing
  deletion. Acceptance must preserve shared work and active leadership, stop
  standing work and channels, tolerate interruption/retry, and identify retained
  categories. No current action fulfils this whole-account operation.
- **Backups and external copies:** document approved restoration and provider
  handling. A disposable restore must not silently reactivate a removed account
  or resume its work. Explain which external copies local controls cannot recall;
  do not imply that live deletion changes old archives or recipients' copies.

These are follow-up scope and acceptance criteria, not delivered features or
permission to change retention policy. KAN-23 defines and verifies the supported
procedure; it does not stand in for implementing these separate product gaps.

## Verification and remaining acceptance

The original disposable SQLite rehearsal in
[test_personal_data_procedure.py](../backend/tests/test_personal_data_procedure.py)
passed: three report/version pairs became two after deleting the selected
personal report; another account's report was inaccessible to the requester;
shared team work remained readable after deactivation and the old token failed.
The account row remained. Existing team-authority tests cover last-manager
protection.

A further isolated rehearsal against released main `13e9525d` passed eleven
selected cases. Mixed paginated results produced only the three agreed personal
versions, with returned filenames and distinct content hashes checked. Deleting
one selected report reduced five reports/six versions to four/four; shared and
other-user data, the retained personal record and account survived deactivation.
Pause/archive controls stopped the selected owner's standing work while another
owner's schedule alone queued a job. No model worker ran. The selected existing
tests also covered retained edition history, active-job cancellation, rollback
and manager/departure safeguards. See the
[rehearsal review note](reviews/2026-10-02-KAN-23-personal-data-procedure.md).

This additional rehearsal did not seed notification preferences, feed tokens,
push devices or delivery outboxes. Their inventory above is source-reviewed,
not a claim of notification erasure or live delivery verification. No real
requester data, private file transfer, production deletion or legal retention
decision was exercised.

KAN-23 remains open until the operator's request-handling and shared-team policy
choices are recorded and the selected supported procedure is verified. Identifying
unsupported steps and concrete follow-up scope is required; completing every
account-wide implementation gap is not a prerequisite for this procedure task.
Do not describe this page as a complete account-wide export or erasure capability.

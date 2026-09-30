# Personal-data requests: current capabilities and proposed procedure

Status, 30 September 2026: capability inventory reviewed for KAN-23. The proposed
operator-assisted policy below awaits the installation operator's confirmation.
There is no account-wide export bundle or complete account-erasure action.
Account deactivation revokes access; it does not erase data.

## Responsibility and scope

Proposed contact: the installation administrator through the installation's
existing private support channel. Verify the requester's identity and exact
account before selecting records. Do not publish personal data in GitHub or Jira.

Proposed team policy: preserve shared team work and resolve responsibility with
the team before changing membership. A person's authorship does not make all
team records personal exports or authorise deleting shared work. This policy
requires the operator's choice; no legal retention period is inferred here.

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
| Audit and usage/allowance records | Administrators can inspect existing audit/usage views | No documented per-account erasure/retention schedule; security and accounting records can survive deletion of content |
| Backups and external copies | Follow the operator's approved backup/restore process | Live deletion cannot remove old archives, downloaded files or data already sent to providers |

Source boundaries: [report deletion](../backend/src/ase/adapters/persistence/reports.py),
[account administration](../backend/src/ase/application/admin/users.py),
[transient input storage](../backend/src/ase/adapters/research_inputs/memory.py),
[original asset records](../backend/src/ase/adapters/persistence/original_asset_models.py)
and [team authority](api/TEAMS_API.md). Each product's API remains authoritative
for the individual action; this inventory is not an account-erasure implementation.

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
a complete account-wide export or erasure.

## Remaining product and policy decisions

A complete request needs a separately approved implementation covering a
scoped account inventory, export manifest and bundle, retention decisions for
audit/usage/credentials, shared-team ownership, scheduled-job dependencies,
idempotent erasure with rollback/retry, and backup-restoration handling.
Acceptance must prove that an export excludes other accounts and team-only work,
that erasure preserves shared data and leadership, and that interrupted removal
cannot leave inaccessible ownership or active background work.

The disposable SQLite rehearsal in
[test_personal_data_procedure.py](../backend/tests/test_personal_data_procedure.py)
passed: three report/version pairs became two after deleting the selected
personal report; another account's report was inaccessible to the requester;
shared team work remained readable after deactivation and the old token failed.
The account row remained. Existing team-authority tests cover last-manager
protection. This evidence is limited to the selected supported path.

KAN-23 stays open while the operator policy and account-wide gaps are unresolved.
Do not use this page as a claim that the gaps above have been implemented.

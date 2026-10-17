# Private-data review and removal

KAN-240 adds an operator-assisted command for private accounts and saved work.
It requires an active administrator's current password on the trusted host.
There is no public deletion endpoint, scheduled account purge or automatic
decision to erase research. Deployment and an individual production removal
require their own authorisation. This document records implemented behaviour,
not evidence that anyone's live records have been removed.

## Review before removal

Run commands from `backend` against the explicitly selected installation. The
command uses normal settings, opens the database and never creates or migrates
its schema. Migration 0095 must already be installed through the approved release
process. Replace the example identifiers with verified account identifiers:

```text
uv run ase private-data preview --operator ADMIN_UUID --owner OWNER_UUID
uv run ase private-data review --operator ADMIN_UUID --owner OWNER_UUID --decision retain --purpose quarterly --expected-revision 0 --days 90
```

`preview` is the default action. It returns table counts, blocker codes, retained
categories, the current necessity review and a fingerprint, without titles,
evidence, encrypted destinations or password values. A blocked inventory can be
partial, especially when a bound is reached. Counts are never permission to
delete through a separate mechanism.

The account-wide review decision is `retain`, `hold` or `remove`. Purposes are
`quarterly`, `account_closure`, `rights_request` and `purpose_complete`. Record
the substantive rationale in the operator's restricted case record, not a shell
argument containing personal material. The database records the decision,
purpose, operator, revision and next review date; the audit records the event.
Review every 90 days or sooner and on account closure/purpose completion.
Use the current revision for subsequent decisions. A stale revision fails.

`hold` never becomes permission when its review date passes. `retain`, a missing
review or an overdue `remove` decision also blocks this command. These are holds
on this manual removal workflow. They do not replace the separate authentication
and operational housekeeping holds, or block existing user deletion operations.
For a preservation requirement, coordinate those controls and restrict ordinary
mutations before recording the hold. Alex Orr owns the installation's review;
this implementation does not claim a completed review of any live account.

## Select a scope

| Scope | Included private records |
| --- | --- |
| `account` | Private reports, schedules, jobs and briefs, profile/avatar, saved conversations, personal configuration, feed credentials, notification preferences, devices, personal webhook destinations, memberships and private per-user state. |
| `report` | Its versions, evidence/annotations, search/map projections, originals, excerpts and related owned checkpoints. |
| `subscription` | An archived, disabled subscription's revisions, editions, attempts, lineage, selected metadata, terminal/pending receipts and owned output reports/checkpoints. |
| `brief` | Its private revisions and linked private subscriptions/checkpoints/output reports. Linked subscriptions must be archived and disabled first. |
| `job` | An inactive, settled checkpoint and its unshared excerpts. Its final report remains; excerpts still used by that report block removal. |

Saved-work scopes require `--target SAVED_WORK_UUID`. Account scope takes no
target and requires deactivation first. The executing administrator cannot
remove their own account. Shared work is excluded, including independently
published team copies of a personal report. Removing membership requires another
active manager for each active team the account manages.

The workflow refuses active jobs, uncertain provider calls, open source budgets,
unsettled subscription attempts, active uploads and released or uncertain
deliveries. It checks row ownership, revision authorship, incoming foreign keys
and recognised structured references in surviving work, including later evidence
used to resolve a different report's forecast. It does not rewrite immutable
history to make a dependency disappear. Free prose containing a UUID is not a
structural reference.

## Apply the exact reviewed inventory

After verifying the request, other people's interests and preservation needs,
record a `remove` decision with the current review revision. Obtain a fresh
preview for the selected scope, inspect all counts and retained categories, then
explicitly apply its fingerprint:

```text
uv run ase private-data review --operator ADMIN_UUID --owner OWNER_UUID --decision remove --purpose rights_request --expected-revision REVIEW_REVISION
uv run ase private-data preview --operator ADMIN_UUID --owner OWNER_UUID --scope report --target REPORT_UUID
uv run ase private-data apply --operator ADMIN_UUID --owner OWNER_UUID --scope report --target REPORT_UUID --fingerprint PREVIEW_FINGERPRINT
```

Apply locks and rechecks current authority, dependencies, execution state, review
and row contents. A changed inventory or blocker refuses the operation. Deletions,
the account marker and the audit record commit together. A failed audit rolls
back deletion. A connection or cleanup failure can leave the outcome uncertain,
including after a successful commit: inspect the selected database and obtain a
new preview before retrying. Do not infer rollback merely from a command error.

An account becomes a permanently inactive UUID stub with a reserved invalid email,
`Removed account` display name and no password. Its security version advances.
Ordinary account updates cannot reactivate it, and stale conversation/tier writes
are refused. This is minimisation, not anonymisation: retained shared history and
audit can still identify its former owner. Create a new account through the normal
process if access is required again.

## Bounds and retained material

One operation permits at most 250 roots per category, 10,000 selected rows and
256 MiB of encoded data plus actual original bytes. Surviving structured references
have a separate 5,000-row/64 MiB bound. Exceeding a bound fails closed. Smaller
saved-work scopes may help with the selected inventory; a global reference bound
requires a reviewed inventory strategy, not raising limits or bypassing checks.
Rows are read in small batches and deleted by captured keys, consistently with
SQLite foreign keys enabled or disabled and PostgreSQL.

The preview explains these retained categories:

- Shared work, other authors' rights, independent copies, team invitations/posts
  and historical account requests/enquiries, under their separate policies.
- Audit and necessity decisions, the inactive identity stub and attribution links.
- AI reservations/usage, allowance totals, operator evaluation runs and policy
  decisions needed for accounting, uncertainty or review.
- Unselected delivery/replay records. Selected disposable receipts are included
  in counts. Receipts attached to retained shared parents remain; deactivation
  prevents new releases but cannot recall messages already released to a provider.
- Backups, off-site archives, provider/mailbox/browser copies and previous exports.
  Follow [backup and restore](BACKUP_RESTORE.md); KAN-243 owns reconciliation before
  restoring or reactivating a backup. Database removal alone does not erase them.
- Other processes' in-memory private inputs until their normal expiry (15 minutes)
  or shutdown. The command does not signal remote processes to clear memory.

Preserve a restricted completion record containing the scoped identifiers,
decision/revision, preview fingerprint, counts, outcome and external-copy actions.
The command does not contact providers or send messages. No live deletion has
been authorised or performed by implementing this ticket.

Migration 0095 stores necessity decisions and permanent removal markers. Its
downgrade refuses to drop a non-empty review table, preventing rollback from
silently losing a hold or allowing a removed UUID to be revived.

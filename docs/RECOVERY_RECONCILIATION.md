# Recovery decisions and external copies

KAN-243 supplies a protected record and a manual pre-reactivation procedure.
Restoring an archive can restore an account, preference or report that was later
restricted or removed. `restore.py` still writes only new targets and never
starts services. Its successful exit proves restoration, not permission to use
the recovered data. This procedure extends [backup and restore](BACKUP_RESTORE.md)
and [personal-data operations](PERSONAL_DATA_OPERATIONS.md).

## Responsibility and coverage

Alex Orr owns the current personal installation's decisions, copy inventory and
recovery approval. A delegated operator must have explicit authority and an
active, current administrator account where a database command requires one.
Record necessity at least quarterly (the command permits 1-90 days), on request
resolution, account closure, purpose completion, and before every activation
from restored data. A review due date never expires a preservation hold.

The encrypted journal contains UUIDs, sequence numbers, action/outcome, purpose,
review dates and selected copy policies. It excludes names, addresses, messages,
report text, credentials, destination URLs and free-text case details. UUIDs still
constitute potentially identifying information. Keep the substantive decision,
identity verification, installation-to-journal mapping and inventory privately,
using the journal's opaque references to link them.

Only `private-data review/apply` writes are automatically journalled. Ordinary
UI/API deletions, account deactivation, channel preferences and earlier actions
are not captured automatically. Record relevant restrictions separately and
retain completion evidence. An empty new journal says nothing about older
decisions. Never treat absence of an entry as permission to reactivate or retain.

## Protect and initialise the record

Provision private directories **outside the checkout, live database directory,
backup roots, release directories and their off-site mirrors**. Keep the key in
an independently protected location and preserve a recoverable copy separately.
Do not reuse the application, backup-encryption or manifest-authentication key.
The application never creates missing history implicitly.

On POSIX, directories and files must belong to the executing operator and allow
no group/other access (normally `0700`/`0600`). On Windows, provision and verify an
NTFS DACL limited to the operator and necessary system administrators **before**
initialisation. `0600` does not establish that DACL; this tool does not validate
Windows ACLs. Do not use shared, synchronised or attacker-writable directories.
Links, junctions and multiply linked files are refused, but trusted directory
ownership/ACLs are also needed to prevent replacement races.

From `backend`, substitute actual absolute protected paths:

```text
uv run ase recovery-record journal initialise --journal JOURNAL_PATH --key KEY_PATH
uv run ase recovery-record journal inspect --journal JOURNAL_PATH --key KEY_PATH
```

Initialisation refuses either existing file. Loss, corruption or a wrong key
stops inspection/writes; do not initialise new history to get past that failure.
The journal uses authenticated Fernet encryption, bounded reads, atomic file
replacement and a separate exclusive lock. A leftover `.lock` is not stolen:
first establish that no operator process is running and investigate the last
outcome before manually removing that specific lock.

Maintain a protected **latest** independent copy after each completed operation
and retain its displayed journal ID and `head_sha256` in the restricted case log.
Encryption detects modification, not replacement with an older valid encrypted
copy. Compare with the independently trusted latest head before recovery. The
journal is limited to 1,000 events and 2 MiB of plaintext; reaching capacity stops
writes. It has no automatic expiry or history-pruning command. Preserve all
generations and obtain a reviewed capacity/migration plan instead of starting
unlinked history. Retain decisions for as long as an affected recoverable copy
exists or a current restriction requires them, with quarterly minimisation review.

## Record actions without overstating their effect

Database mutations now require both paths:

```text
uv run ase private-data review --operator ADMIN_UUID --owner OWNER_UUID --decision hold --purpose rights_request --expected-revision REVIEW_REVISION --journal JOURNAL_PATH --journal-key KEY_PATH
uv run ase private-data apply --operator ADMIN_UUID --owner OWNER_UUID --scope report --target REPORT_UUID --fingerprint PREVIEW_FINGERPRINT --journal JOURNAL_PATH --journal-key KEY_PATH
```

Follow [private-data removal](PRIVATE_DATA_REMOVAL.md) for authority, current
reviews, preview, ownership and execution guards. The durable journal intent
precedes the SQL mutation; completion follows database/audit commit. A committed
`review(remove)` is permission for later work, **not a completed deletion**.
A `removal` with `committed` status records a completed scoped database removal.
Sequence is intent order, not wall-clock or completion order.

An uncertain commit or journal completion leaves `pending` evidence. Further
journalled writes stop. Keep services offline during recovery and inspect the
exact target, audit and private records before deciding whether it applied.
Never infer rollback from an error. An authorised operator may resolve that
specific intent only after retaining investigation evidence outside the archive:

```text
uv run ase recovery-record journal resolve --journal JOURNAL_PATH --key KEY_PATH --event EVENT_UUID --operator OPERATOR_UUID --outcome applied --evidence EVIDENCE_SHA256 --head CURRENT_HEAD_SHA256
```

Use `not_applied` only with affirmative evidence that no mutation committed.
Resolution preserves the original intent and records the operator, time and
evidence digest. It is an operator attestation, not an automatic database check.
It does not permit activation. File commands rely on trusted-host/key access;
their operator UUID is attribution, not password authentication.

For a request received outside the removal command:

```text
uv run ase recovery-record restriction --journal JOURNAL_PATH --key KEY_PATH --operator OPERATOR_UUID --owner OWNER_UUID --restriction objection --purpose rights_request --days 90
```

Supported instructions are `deactivate`, `objection`, `email_opt_out`,
`digest_opt_out`, `subscription_opt_out`, `push_revoke` and `feed_revoke`.
Only `subscription_opt_out` requires `--target SUBSCRIPTION_UUID`.
These are `recorded` instructions: they do not disable accounts, cancel delivery
or delete anything. Apply the relevant supported controls separately, retain the
outcome and resolve conflicting/current restrictions manually. Never lift a hold
just to make an old deletion command pass. Consent, objections and their reversal
need current authority and case evidence; there is no automatic unrestriction.

## Before every restored installation is activated

1. Keep web access, workers, feeds, schedules and outbound email/push/webhooks
   stopped and network-isolated. Restore to fresh targets only. Verify the source
   manifest, selected database and compatible application/schema revision. Do not
   run older code that ignores permanent removal markers.
2. Obtain the latest independently trusted journal/key and restricted case/copy
   inventory. Confirm the installation mapping and compare the trusted head.
   Inspect **all** entries, not just dates after archive creation: backup timestamps
   are not a database transaction watermark. Investigate pending intents first.
3. Reconcile pre-journal and unrecorded actions, including UI deletions, role and
   membership changes and channel opt-outs. Missing history is a blocker until
   the operator completes and records a scoped investigation. Inspection always
   reports `activation_authorised: false`; it never certifies completeness.
4. Establish current operator authority independently of the restored snapshot.
   A restored account that has since been removed or deactivated must not act as
   administrator. Follow approved administrative recovery if current credentials
   are absent. Do not use old privileges as proof of current authority.
5. Reapply current objections/restrictions and holds first through supported
   administrative/channel controls. Appoint replacement team managers or archive
   teams through the normal process where required. Use normal opt-out/revocation
   services so pending/released delivery states are handled correctly. Changing a
   preference flag directly is not equivalent. Keep uncertain deliveries offline.
6. For each **committed removal**, verify the exact owner, personal/shared scope
   and current case authority. Obtain an explicit current necessity review and
   fresh preview before applying the ordinary removal command to the explicitly
   selected recovered database. Do not renew a removal review over a newer/current
   `hold` or `retain` decision. Resolve that conflict separately while offline.
   Scope/ownership changes, active jobs, unsettled provider calls and dependency
   blockers need investigation; the journal never bypasses those guards.
7. Check results and preserved shared/other-user work. A missing-target error can
   also mean different ownership: investigate, do not silently mark it reconciled.
   For an already removed account, verify its inactive minimised identity, removal
   marker and absence of the selected private graph. Do not clear the marker to
   retry. Verify old sessions/passwords fail and standing work/delivery cannot
   resume for restricted owners. Review restored secrets/configuration separately.
8. Retain a protected, target-specific reconciliation record: operator/time,
   source manifest hash, application revision, verified installation/journal ID,
   latest head, exact restored target and its post-reconciliation snapshot/hash,
   each action/evidence reference, retained material and unresolved blockers.
   A path alone cannot identify a database that has since been replaced. A partial
   run is a partial run; no clean global receipt is generated by this tool.
9. Obtain separate operator approval before activation. If the journal, target,
   configuration or current decisions change afterwards, reconcile again.
   Production restore, destructive changes and deployment retain their approval
   requirements. No code test or ticket closure supplies that approval.

## External-copy reviews and selected policy

Alex owns the following inventory, reviewed quarterly and at request resolution,
with a review before recovery/activation. The table records known software rules;
it does not invent installation-wide age limits or claim a live review occurred.

| Copy | Known rule and review action |
| --- | --- |
| Scheduled archives | Helper default newest 30, minimum 3, after successful verification. The 11 October observation found the default and no off-site override. Recheck the current selected count, oldest archive and holds; counts are not maximum ages. |
| Manual/off-site archives | No application age or deletion guarantee. Inventory each destination, recovery purpose, selected period/count, hold and provider responsibility. Unknown policy remains an open review action. |
| Release copies | Pruner default 5, minimum 2; preserves current/latest/rollback and images in use. Dry-run is default. Review actual selection and database backups in release directories before approved pruning. |
| Mailbox correspondence | Review the privacy/request case on resolution and quarterly. Record a justified selected period or hold for the case; do not infer that deleting the app enquiry deletes Yahoo or recipient copies. |
| Exports/browser/recipient copies | Inventory copies under operator control and their selected policy. Contact/provider actions are separately authorised. No application command recalls downloads or sent messages. |
| Offline public snapshots | Disposable live/satellite caches are excluded from backups. Inspect offline files at shutdown, restart and quarterly; runtime access expiry is not disk erasure. Remove only through an approved targeted action after checking purpose/holds. |

Record actual operator-selected values, not example defaults:

```text
uv run ase recovery-record copy-review --journal JOURNAL_PATH --key KEY_PATH --operator OPERATOR_UUID --reference COPY_INVENTORY_UUID --category scheduled --keep-count SELECTED_COUNT --purpose quarterly --days 90
uv run ase recovery-record copy-review --journal JOURNAL_PATH --key KEY_PATH --operator OPERATOR_UUID --reference CASE_INVENTORY_UUID --category mailbox --hold --purpose rights_request --days 90
```

An age policy uses `--max-age-days SELECTED_DAYS`; count and age can both be
recorded. The tool requires a selected period/count or explicit hold. These are
policy records, not pruning jobs or proof of erasure. Keep unknown/unselected
values in the restricted review action list until decided. Protect held archives
outside the scheduled/pruner namespace or suspend pruning under approved change
control: those existing pruners do not read this journal's holds.

## Disposable verification

`test_recovery_drill.py` creates a real SQLite snapshot before an account removal,
another owner's hold/objection and a permission-only decision. It restores through
the normal new-target script and manually reapplies guarded actions. It verifies
removed private work and identity cannot return, restricted passwords fail,
shared/held/permission-only work survives, repeat removal stops at the permanent
marker and ownership mismatch is not treated as successful reconciliation.
No service or network worker starts. Other tests cover uncertain commits,
journal-finalisation failure, stale reviews, tampering, capacity and unsafe paths.

This is a disposable SQLite recovery drill, not a production or PostgreSQL restore
claim. The scheduled helper's `drill` remains decrypt/authenticate/verify-only.
Perform a separate full disposable recovery rehearsal for the selected production
database and current backup configuration before approving an actual recovery.

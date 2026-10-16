# Authentication record retention

KAN-238 provides bounded housekeeping independent of logins, account activity and
feed configuration. Automatic erasure is **off by default**. Deployment alone does
not enable it. Authentication expiry continues to reject invalid credentials even
while their stored rows await erasure.

These are operational defaults selected for a restricted research installation,
not statutory deadlines. The operator reviews necessity quarterly and after an
incident or change of use, and records any reason to vary the decision window.

| Records | Eligibility and purpose |
| --- | --- |
| Decided account requests | Approved/rejected decisions at least 90 days old. This allows a quarterly review of access decisions without keeping identity/reason indefinitely. `ASE_ACCOUNT_REQUEST_RETENTION_DAYS` permits 30 to 3650 days. Pending, unknown-status and undated decisions are retained for explicit review. |
| Activation/reset links | Seven days after first becoming unusable through expiry or recorded use. This short incident investigation window retains hashes, not usable link secrets. Unused valid links remain. |
| MFA challenges | At expiry or recorded consumption, erase the row including code hash and pending encrypted enrolment secret. Successful consumption already clears embedded secret fields. Audit evidence has its separate retention policy. |
| Pending TOTP | At its deadline, clear only pending secret and deadline fields. Keep the enabled factor, replay-protection step, email MFA setting and recovery codes. |
| Refresh families | All tokens must have expired at least 91 days ago. This conservative post-terminal investigation window uses the existing maximum refresh lifetime of 90 days plus a day. Every ancestor remains while a newer descendant is within that window, preserving replay detection. |
| Family activity/revocation | At least 91 days old, with no remaining token or push device. Revocation markers remain throughout token cleanup. |
| Expired-family browser push | Drain receipts, then remove empty devices and their encrypted subscriptions before deleting that family's last token. This avoids unlimited cascades and retains an eligibility/ownership anchor while processing a backlog. |

All cutoffs are inclusive (`<=`), with one UTC time captured for the batch. The
clock must be correct. Malformed/missing decision dates and pending TOTP without
a deadline are not guessed. Tokenless legacy push devices are left to the existing
push authorisation/cleanup path and KAN-241's independent maintenance scope.

## Preview and controlled rollout

Run commands from the backend directory against the explicitly selected database,
using the installation's established environment. The command does not migrate or
create schema. Check database selection privately; do not paste credentials into
ticket evidence or shell history.

```text
uv run ase auth-retention
uv run ase auth-retention --apply
```

The first command only reports candidate counts. The second explicitly applies one
batch. Counts are capped at 100 per category, not a total backlog inventory. Preview
does not simulate dependency removal: a device or family that becomes eligible
after its children are erased may appear only in a later preview. Concurrent changes
can also alter the actual result. Neither output includes identities, token hashes,
session identifiers, ciphertext or a database address.

Each committed batch changes at most 100 rows in each of nine categories, at most
900 retained rows in total. The transaction takes the administration guard, then
account locks, and rechecks eligibility after waiting. Failed transactions roll
back; repeats continue the backlog and become no-ops once it is empty. Row limits
bound deletion and memory use, not database scan time. Large unindexed histories
may still need a maintenance window and measured query planning.

Before applying to an installation, record the intended database, preview counts,
policy approval, current recovery arrangements and any holds. Existing backups and
exports require the separate KAN-243 reconciliation process; a local erase cannot
remove external copies. This ticket's disposable tests are not production approval.

To enable the minute-by-minute worker after that review, set
`ASE_AUTH_RETENTION_ENABLED=true` and restart the API. It runs with feeds disabled,
handles failures without logging record contents, and stops before database disposal.
Monitor the `auth_retention` worker heartbeat and count-only completion/failure events.
Review a capped backlog over successive cycles. Disabling the worker stops future
batches, not an in-flight transaction; wait for a clean stop before changing policy.

## Holds and scope

Set `ASE_AUTH_RETENTION_PAUSED=true` and restart **all** API processes to suspend
this housekeeping. The CLI reads the same setting and cannot override it with
`--apply`. Until every old worker has stopped, a configuration edit is not an
effective hold. Record the incident/reference, owner, reason, start and review date
in a restricted operator record. Keep the pause until the authorised review releases
it; the application never expires a hold automatically. This is a conservative
global hold on these nine maintenance categories, not per-person erasure authority.

A housekeeping hold does not suspend security operations: logout, revocation,
factor removal, user device removal and the existing push worker's seven-day receipt
retention still operate. It is not a universal forensic preservation mechanism.
If preservation beyond these categories is required, establish a restricted,
authorised evidence copy and its own review/removal date. Do not preserve usable
authority by disabling revocation. Audit and usage records remain KAN-239 scope.

The previous unbounded family cleanup during logout/revocation has been removed.
Credential invalidation still commits immediately; physical erasure now follows
only this explicit maintenance policy. With automatic cleanup disabled, operators
must run authorised batches or continue the documented quarterly review.

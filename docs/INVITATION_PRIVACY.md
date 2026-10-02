# Exact-handle invitation privacy

An exact username may receive an invitation even when directory discovery is off.
Every authorised username submission creates an opaque sender receipt, including
unknown, invalid, inactive, protected-administrator, duplicate and existing-member
handles. A receipt confirms submission only, never account existence or delivery.
Sender lists, totals, pagination, pending capacity and withdrawal revisions use
these receipts independently of recipient responses.

Before acceptance, opaque receipts contain no resolved recipient UUID, display
name or username. Declines and recipient-side authority failures remain private;
the sender sees a pending receipt until its fixed seven-day expiry or withdrawal.
Acceptance is consent to join: the matching receipt gains a snapshot of identity
at acceptance. Later profile changes never update receipt identity. Invitations
sent through the opt-in directory retain the already-disclosed identity snapshot.

Duplicate username submissions receive separate receipts. Only the first eligible
submission is linked to a delivered invitation. Withdrawing an unlinked duplicate
receipt cannot cancel another submission. All receipts consume the same team
pending allowance; recipient declines cannot silently free capacity. The existing
20-per-account-per-hour username limiter still applies.

Migration 0082 follows the released history through 0081 and retains recipient
inboxes and accept/decline behaviour. Historical
unknown submissions were not recorded, and original submitted usernames cannot be
reconstructed. Unaccepted historical deliveries are therefore absent from sender
history. Managers can still withdraw a historical delivery using its previously
known ID. This route returns the same empty success response for missing,
already-resolved and revoked legacy IDs, ignores obsolete legacy revision values,
and never adds them to sender history. Modern deliveries must use their sender
receipt for withdrawal. Accepted historical deliveries have consent and retain a receipt without
reconstructing a current username. Plan a manual rollout with a verified backup;
downgrade requires a reviewed matching backup rather than reintroducing the old
sender disclosure through an automatic schema downgrade.

# KAN-113 browser push boundary review

The service worker has two listeners: push and notification click. It has no
network fetch listener, cache, cookie/token access, authenticated background work
or arbitrary navigation target. It accepts only a UUID payload and constructs
a same-origin authenticated alert URL. Generic visible notification text meets
the browser requirement without disclosing an alert title or location.

Device registration requires a live session, explicit browser permission and
current account authority after external DNS validation. Keys are validated as a
P-256 public point and a 16-byte auth secret. Endpoint/provider/port validation,
fresh public DNS resolution, pinned TLS with original SNI, redirect refusal and
disabled environment proxies guard outbound requests. Existing task-local HTTP
log protection prevents paths, headers or endpoints appearing in library logs.

The complete subscription is stored as `web_push_devices.encrypted_subscription`
under the existing secret cipher; only its hash and random device ID leave the
repository. This column must be included in the KAN-17 encryption-rotation
inventory when the parallel security work is integrated. Production VAPID
credentials are optional environment secrets and are not generated at startup.

Devices and outbox rows are explicitly deleted in the same transaction as family
revocation or account security changes. Child cleanup is explicit because SQLite
connections may lack foreign-key enforcement. The worker rechecks current session
and security version, account state, active membership and alert scope before
every external attempt. Administrator inspection rights are removed from recipient
visibility. Locks end before external work; no claim can recall data after vendor
acceptance, so payload minimisation and authenticated clicks remain necessary.

Admission uses bounded SQL with a unique device/alert receipt and an anti-join
against previously seen receipts. Timestamp-plus-random-UUID cursors were rejected
in review because later commits can share a timestamp and sort before the cursor.
Receipt retention exceeds the eligible one-day alert window. Claims use conditional
updates and interrupted/ambiguous outcomes become terminal uncertain records.
There is no automatic retry that could duplicate an uncertain acceptance.

Focused tests use synthetic keys, mocked provider transports and isolated SQLite
connections. They cover cleanup, scope loss, late commits, competing claims, unsafe
endpoints, redirects, payload and logging boundaries, browser permission failure,
unsubscribe and worker navigation. Optional PostgreSQL concurrency and physical
Android/iOS vendor delivery remain explicit release acceptance checks. Independent
security review identified malformed-URL handling and timestamp-cursor omission
risks; both were repaired. The reviewer independently passed five checks for
same-time late commits, no replay, malformed endpoint inputs and stale claims,
with no further actionable finding in the reviewed boundary.

## Acceptance clarification, 2 October 2026

The preceding text records the original review checkpoint. KAN-113 explicitly
requires a manual Android Chrome check, which remains unperformed. Physical iOS
testing is a recommended platform release check when supporting iPhone/iPad, not
an additional Jira closure criterion. Neither fixture delivery nor a successful
provider response proves physical device receipt. Later PostgreSQL, rotation
inventory and independent review evidence is recorded in the
[final integration review](../reviews/2026-10-01-final-notification-integration.md).

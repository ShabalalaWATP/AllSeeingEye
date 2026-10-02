# Browser push notifications

Browser push is off by default. Open **Account, Notifications** and choose
**Enable push on this browser**. The permission prompt follows that button press.
Each browser is registered separately, with at most ten devices per account.
Settings lists registered devices and lets the account remove any of its devices.
Disabling browser permission also stops receipt; registration failures unsubscribe
the newly created browser subscription.

Notifications travel through the browser vendor's push service. The encrypted
payload is only an opaque alert UUID. The lock screen shows a generic notification,
without an alert title, summary, location, report text or source material. Clicking
opens an app URL on the same origin. The app then fetches that alert through normal
authentication and current object authorisation, including after a new sign-in.

The minimal service worker handles only `push` and `notificationclick`. It has no
fetch interception, API response cache, offline authentication or background token
refresh. It registers at the existing same-origin root scope; the existing CSP
already permits that worker and is unchanged.

## Browser support

Use a secure context, normally HTTPS, and a browser implementing Service Workers,
PushManager and Notifications. Support is detected by capabilities rather than a
user-agent string. Chrome, Firefox, Safari and Edge provider endpoints are accepted
only at the configured built-in HTTPS provider domains. Unsupported providers
fail closed and need a reviewed code change before use.

On iPhone and iPad, add the app to the Home Screen and launch it there before
opting in. Apple documents standards-based push for Home Screen web apps from
iOS/iPadOS 16.4. Permission must follow a user gesture and pushes must display a
visible notification. See [Apple's Web Push guide](https://developer.apple.com/documentation/usernotifications/sending-web-push-notifications-in-web-apps-and-browsers)
and [WebKit's Home Screen guidance](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/).

## Operator setup

Configure `ASE_ENCRYPTION_KEY` using the existing secret-storage procedure. Browser
endpoint credentials are encrypted with that key. Then generate a VAPID key once
in an operator-controlled private directory, using the installed dependency's
`vapid --gen` command (or `uv run --project <backend-path> vapid --gen`). This writes
`private_key.pem` and `public_key.pem` in that directory. Keep those files outside
the repository. Put the concatenated base64 body of `private_key.pem`, excluding
the PEM boundary lines, in the deployment secret `ASE_WEB_PUSH_VAPID_PRIVATE_KEY`.
The accepted format is base64 DER, or the library's base64url raw private key.

Set `ASE_WEB_PUSH_VAPID_SUBJECT` to the operator contact URI, such as
`mailto:operator@example.invalid` with the real contact address substituted. Both
VAPID settings are required together. The public application-server key is derived
from the configured private key and returned through the authenticated settings
API. The app never generates or rotates a production key on startup. Replacing
the VAPID key requires browsers to unsubscribe and explicitly enrol again.

Encryption and VAPID signing use the maintained standard implementations
[pywebpush](https://pypi.org/project/pywebpush/) and
[py-vapid](https://pypi.org/project/py-vapid/). The application uses their cryptographic
operations and its own existing pinned HTTP transport. Both libraries use MPL-2.0;
their source is unmodified. Network calls do not use their convenience send APIs.

## Authority, limits and delivery outcomes

Each device belongs to a user, the session family that registered it and that
account's security version. Successful sign-out, session revocation, account
deactivation, role changes and security-version changes delete the device and
queued receipts transactionally. The browser also unsubscribes when its local
session ends. If sign-out cannot reach the server, local browser unsubscribe is
best effort; normal server session expiry and pre-send checks still apply.

Immediately before dispatch, the worker checks the current account, session,
device and alert visibility. Administrator inspection privileges do not expand
notification scope. Team delivery requires active membership of an active team.
An accepted notification cannot be recalled after a subsequent access change;
the payload contains no private details and the app checks access again on click.

Admission checks up to 100 due devices per tick and 25 new alerts per device.
Only alerts fired since that device's opt-in and within the last day are eligible.
Unique device/alert receipts prevent repeats, including when a later database
commit has the same alert time and a lower random UUID. Receipts are retained for
seven days, longer than the eligible alert window. One worker can claim a receipt;
at most 25 external attempts run per tick. Registrations are limited to 20 per
hour per account in addition to the ten-device storage limit.

Every external attempt resolves and validates all destination addresses, pins a
public address, verifies TLS with the original host and disallows redirects and
environment proxies. HTTP library diagnostics are suppressed within the secret
request context. Neither endpoint credentials nor transport exception text are
logged. A provider's 404 or 410 response deletes the subscription. Definite
rejections are terminal; timeouts and interrupted claims are uncertain and never
automatically retried. `TTL: 0` asks the vendor to discard a notification when the
device cannot receive it immediately. Push is best effort and the in-app alert
remains the durable source of record.

## Validation and release acceptance

Automated checks cover opt-in defaults, encrypted credentials, opaque payloads,
provider and SSRF validation, pinned TLS, no redirects, credential-safe logs,
session/security cleanup, revoked memberships, scoped device removal, late commits,
competing SQLite workers, interrupted claims, browser subscribe/unsubscribe,
permission denial, setup failure and the worker's same-origin click handling.
The optional PostgreSQL concurrency test requires an isolated disposable database.

KAN-113 requires a manual Android Chrome check. For this check, an operator should
configure test-only VAPID credentials and verify an installed app against a chosen
synthetic alert. Confirm permission, receipt, authenticated click, removal and
sign-out. This required manual check remains unperformed.

If iOS is part of the deployment, repeat the check on a supported installed
iPhone/iPad app as a recommended platform release check. It is not an additional
KAN-113 closure criterion. No physical device check was performed by this
implementation, no live push was sent, no real provider credential was used and
no delivery was enabled.

# Security and privacy

[Documentation](README.md) · [Architecture](01_ARCHITECTURE.md) · [AI](AI.md) · [Self-hosting](DEPLOYMENT.md)

The app handles accounts, private research, saved reports, provider credentials
and untrusted public material. Its controls are designed to keep access explicit,
limit external work and preserve the distinction between source content and
instructions. These are implemented safeguards, not a security certification.

## Accounts and shared work

Passwords use Argon2id hashing and a common-password check. Account requests need
administrator approval. Administrators must enrol and verify multi-factor
authentication before entering the administration workspace. Authenticator and
email options depend on the installation's configuration. When email delivery is
configured, an administrator's first authenticator is bound only after a code sent
to the account address is confirmed.

Password hashing runs in a small bounded worker pool so sign-in load cannot stall
other requests. Public sign-in endpoints are limited per client, with IPv6 clients
grouped by /64 prefix. Account and reset requests also have installation-wide hourly
caps, and the pending account request queue has a maximum size. The per-email
sign-in budget counts failed attempts only. Each account has a budget of failed
second-factor proofs across challenges and methods, and of directory username changes;
a taken username is reported as unavailable whoever holds it. These limits
are held in memory and reset when the API restarts.

Refresh families keep a server-owned `last_activity_at`. Their idle limit is
180 minutes by default, with a separate optional administrator override, both
bounded to 5–1440 minutes. Only explicit activity extends it, at most once per
minute per family. Automatic refresh, polling, streams and scheduled work are
passive. Expiry is checked before accepting activity, including refresh carrying
`x-ase-activity: 1`. A CSRF-protected heartbeat is bound to the original bearer
family, so changed shared cookies cannot extend another account's session.

Shared access checks remain read-only to preserve caller-owned transactions.
Expired refresh, heartbeat or logout transactions durably revoke the family,
remove its push registrations and record `session.idle_expired` once. Passive
fences reject expired sessions without committing unrelated writes. Cached checks
are bounded by the observed idle deadline; streams recheck within the configured
session interval and send `access.changed` before ending for idle expiry.
[Idle session operation](SESSION_IDLE_TIMEOUT.md) covers the warning, migration
and limits of this policy.

Access tokens are short-lived and held in browser memory. Refresh sessions use
an HttpOnly cookie, server-side records and rotation. Protected requests check
the current account and session state. Routes that release private material after
slow work re-validate through a release fence first. Fences and streams may reuse a
check for a short window unless a committed session or access change has been
signalled since (ADR 0021). Streams also recheck access; the browser invalidates
scoped state when authority changes.

Personal records are visible to their owner and administrators. Team records are
visible to current members and administrators. Object-level checks cover saved
research, report versions, exports, searches and background work. Membership is
not permanent authority: removal, account deactivation and team archiving affect
subsequent operations. Archived work remains readable under the applicable scope.

Sensitive mutations coordinate account and team checks with concurrent authority
changes. Model and network calls run outside those database locks, and sensitive
results are checked again before persistence or release. Already downloaded
copies cannot be recalled.

## Untrusted sources, files and model output

Public-feed requests use destination checks, redirect checks, bounded responses
and deadlines. Private and local model endpoints are a separate, deliberate
administrator choice, needed for self-hosted models. A source URL cannot silently
become permission to use the administrator's model endpoint.

Supplied documents and media are parsed under time, size and resource limits.
The Compose parser has no network access and does not receive application secrets.
Native parsing uses an isolated subprocess and refuses extraction when required
limits cannot be installed.

External text and AI output are treated as data. The interface renders structured
text and validated links. Report validation checks structure, citations and
assessment rules; it cannot prove the truth of source claims or eliminate all
prompt-injection risk. See [AI](AI.md) and
[reporting and assessment](03_DOCTRINE_AND_REPORTING.md).

## Credentials and durable data

Provider credentials and authenticator secrets are encrypted using the configured
application encryption key. The UI does not return saved full provider keys.
Real environment files are excluded from version control. Logs and errors must
avoid credentials, raw provider responses and other secret-bearing content.

Keep the encryption key recoverable separately from the database. Replacing it
makes existing encrypted values unreadable. Database backups can contain private
research, evidence excerpts and personal information, even when those excerpts
came from public websites.

Raw live events have bounded in-memory retention. So that restarts are not blank,
the same public events are also kept in one disposable snapshot file
([ADR 0022](adr/0022-live-store-snapshot.md)): size-capped, replaced atomically,
owner-only where the platform supports it, strictly validated on load, never a
symbolic link and never backed up. It holds no alerts, sessions, credentials or
private inputs. Set `ASE_LIVE_SNAPSHOT_PATH` empty to disable it.

Reports deliberately preserve selected evidence. Private supplied inputs and
selected original assets have their
own retention rules; inspect the workflow rather than assuming all inputs are
permanent or all are immediately deleted.

The [personal-data operations inventory](PERSONAL_DATA_OPERATIONS.md) distinguishes
supported record exports/deletion from account deactivation and the remaining
account-wide gaps. This installation uses the documented operator-assisted
route and administrator contact; deactivation must never be described as erasure.

## What may leave the installation

| Feature | Outbound information |
| --- | --- |
| Feed collection and research connectors | Requests, source-specific query terms and the configured contact identifier |
| Map and reference services | Requests for the tiles, catalogues or data needed for the view |
| AI features | Relevant questions, selected evidence, extracted text or sanitised images sent to the configured model |
| Optional fresh web research | Public research question and selected public scope sent to the compatible search provider |
| Email | Account messages and verification codes, plus alert, digest and subscription emails a user opts into, through the configured mail service |
| Archive capture (on by default; `ASE_ARCHIVE_ENABLED=false` turns it off) | URLs cited by saved reports sent to the Internet Archive after generation |
| Optional installation alert webhook | Alert notifications sent to the destination the operator configures |
| Optional user alert webhooks | Alert notifications sent to HTTPS destinations that users or teams register for their alert rules |
| Optional browser push | An opaque notification identifier sent through the browser vendor's push service to devices a user enables |

Enabled background collection based on private plan terms can disclose those terms
to the queried public provider. Supported private-file research does not
implicitly turn the extracted content into public feed queries, but model analysis
can still send it to the chosen AI provider.

Self-hosting controls where the application and its database run. It does not make
external source requests, map tiles or cloud model calls offline. Review provider
terms and account retention settings for the material you intend to handle.

## Operating the app

Use HTTPS for hosted access, stable protected secrets and a controlled
administrator account. Keep the API, database and parser behind the intended web
boundary. The [self-hosting guide](DEPLOYMENT.md) covers the portable requirements;
installation-specific access and recovery instructions belong in private operator
records.

CI checks dependencies, source code and container images alongside tests and type
checks. Passing those checks is useful evidence, not proof that an installation
has no vulnerabilities. Keep dependencies current, review changes and test
[backup restoration](BACKUP_RESTORE.md) with your own storage and key handling.

Reducing published server details avoids unnecessary disclosure. It does not
replace patching, authentication, access controls or a reviewed configuration.

## Signed-out pages

The sign-in, account request and password pages, and the optional product page at
`/enterprise`, work without a session. `GET /api/site` tells them, without
authentication, whether `ASE_PUBLIC_PRODUCT_PAGE_ENABLED` is on (off by default).
It returns that single boolean, uncached, and reads no database or session; any new
field there is public and needs a security review. If the request fails, the page
stays hidden.

The flag controls presentation, not access. The page's script is a static asset any
visitor can fetch, so it must hold only public copy. It renders fixed, illustrative
content: no live events, no account data, no third-party scripts, frames or fonts,
and no change to the content security policy. Public copy must not name sources whose
terms forbid commercial or promotional use, or whose reuse terms are unclear; a unit
test checks the page content against a list of such sources.

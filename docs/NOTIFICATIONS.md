# Subscription email and private feeds

These channels are off until you enable them. Existing in-app subscription events
continue independently of SMTP. No migration adds recipients.

## Subscription email

Open **Account, Notifications**. The destination is your account email address.
First enrol email verification under **Account, Security**, which proves ownership
of the address. Provisioned accounts are not assumed to own their email address.
Enabling email notifications requires this verified factor, even if you also use
an authenticator. Removing it stops future notification sends.

Enable **Allow subscription emails to my account address**. Beside a subscription,
open **Email preferences** and choose **None**, **Material changes** or **Every
edition**. The separate attention checkbox includes blocked, paused, failed and
needs-review edition transitions, including those without a completed report.
Each recipient manages their own preferences. Administrators' ability to inspect
someone else's personal subscription does not subscribe them to its emails.

Messages contain a link, an event label and a preference-management link. They
never contain report prose, evidence or source titles. Subscription names require
a separate account-level opt-in because a topic name can itself be sensitive.
An account opt-out stops all pending subscription email; a per-subscription
opt-out affects that subscription. A message already accepted by a relay cannot
be recalled.

Configure the existing `ASE_SMTP_*` settings described in [email setup](EMAIL_SETUP.md)
and [MFA operations](MFA_OPERATIONS.md). TLS certificate verification is mandatory.
When email is unconfigured, the UI says so and intents remain unavailable. The
subscription and in-app events still work. No real SMTP settings or messages were
used during implementation.

### Delivery outcomes and recovery

Edition publication and attention transitions insert email intents in the same
transaction as the edition change. A unique edition/event/recipient key makes
enqueue retries harmless. Account and subscription preferences, account activity,
current personal/team access, email confirmation and subscription availability
are checked immediately before the external call. Team email requires current
membership of an active team. Access changes cancel pending delivery with a fixed,
non-sensitive reason code.

The worker claims up to 25 intents per tick with a conditional database update.
Concurrent workers cannot own the same intent. Claims are committed before SMTP;
account and administration locks are released before network work. The practical
boundary is the final authorisation check immediately before sending, not the
ability to recall a message after a later permission change.

| State | Meaning and recovery |
| --- | --- |
| `pending` | Not attempted yet, or a definite failure eligible for retry. |
| `sending` | One worker owns the external attempt. |
| `sent` | The relay accepted the message; inbox delivery is not established. |
| `unavailable` | SMTP is not configured. Rechecked after 15 minutes. |
| `failed` | Three definite failures exhausted retries. |
| `cancelled` | Current access, availability, confirmation or preferences prohibit delivery. |
| `uncertain` | Acceptance is unknown, including timeout or interrupted worker. Never automatically resent. |

Definite failures retry after five minutes times the attempt number, at most
three attempts. A claim older than two minutes is conservatively recorded as
uncertain. An SMTP response lost after acceptance can therefore cause an
uncertain record even though the recipient received a message. Exactly-once SMTP
delivery is not promised. Review relay evidence before any manual recovery; do not
reset an uncertain intent to pending on assumption. Users can always open the
subscription in the app. This version provides no manual resend action.

One subscription supports up to 100 registered recipient preferences. The worker
and enqueue query have matching bounds. Intents retain IDs and outcome metadata,
not addresses or report content. Errors use fixed reason codes and never record
SMTP exception text.

## Private Atom feed

Open **Account, Notifications** and select **Enable feed**. Copy the URL, username
and password into a feed reader supporting HTTP Basic authentication. The
password is shown once. **Replace feed token** invalidates the previous token;
**Revoke feed token** disables access immediately.

The password is a random feed token, stored only as a hash. It has read-only scope
for this feed, not access to the general API. To keep it out of URL histories,
referrers and ordinary access logs, the URL does not contain the token. Use your
reader's authentication settings, not an embedded `user:password@host` URL.
Readers without separate HTTP Basic authentication settings are unsupported.
Use HTTPS outside local development and never configure proxies to log
authentication headers.

The feed returns the latest 100 currently accessible alerts and completed
subscription editions. It discloses truncation and contains no summaries, report
prose or evidence. Generic labels are the default; including alert and subscription
titles requires explicit opt-in. Administrator inspection privileges do not
include other users' personal work in the feed. Current team membership is checked
on every read. Feed readers may store or synchronise fetched entries elsewhere;
revocation cannot erase copies they already hold.

Account deactivation and security-version changes invalidate feed access. A feed
is independent of normal browser sessions, so signing out alone does not revoke
it. Reads are limited to 12 per minute per token and 60 per minute per client IP,
with `Cache-Control: private, no-store` and `Referrer-Policy: no-referrer`.

## Validation and remaining acceptance

Offline tests exercise scoped API access, token rotation and invalidation, XML
escaping, bounded history, recipient policies, transaction rollback, competing
SQLite dispatchers, opted-out/deactivated recipients, disabled transports, bounded
retries and uncertain SMTP outcomes. SMTP tests use synthetic connections.
PostgreSQL concurrency tests require `ASE_NOTIFICATION_POSTGRES_URL` pointing
only to an isolated disposable database; they are skipped without one.

Before release, verify an operator-configured relay with synthetic content and a
chosen real feed reader over HTTPS. These operational checks are not proved by
the offline suite. Daily digests, per-rule registered destinations and Web Push
remain separate delivery work and are not included by these controls.

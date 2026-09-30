# Email notifications and private feeds

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

**Material changes** email works independently of the subscription's in-app change
alert setting. It compares successive saved reports when a recipient has opted in,
without enabling in-app alerts. With neither channel enabled, publication does not
add change-alert state or notification intents.

Messages contain a link, an event label and a preference-management link. They
never contain report prose, evidence or source titles. Subscription names require
a separate account-level opt-in because a topic name can itself be sensitive.
An account opt-out stops all pending subscription email; a per-subscription
opt-out affects that subscription. A message already accepted by a relay cannot
be recalled.

An opt-out permanently cancels matching pending or unavailable intents. Claims
already marked sending become uncertain because acceptance may have happened.
Re-enabling a channel never revives those earlier intents, even when no worker
ran between the preference changes.

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

## Daily digest

Under **Account, Notifications**, enable account email first, then **Send a daily
digest**. Choose an IANA time zone (for example `Europe/London`) and an hour from
0 to 23. Defaults do not enrol anyone. Disabling account email also disables the
digest, so enabling account email again requires a fresh digest opt-in.

The digest contains counts and authenticated app links, never titles, source
material or report text. It counts alerts and currently completed, needs-review
or failed research jobs in a saved half-open interval: the start is included and
the end excluded. The first interval starts at opt-in; subsequent intervals start
where the last scheduled interval ended. Job counts use their terminal status
and update time when the digest is prepared. Administrator inspection access
never expands the recipient's personal and active-team scope. Counts are read
again immediately before delivery, so revoked access cannot survive in a stored
message body. Deleted or expired records cannot contribute to historical counts.

Forecast counts use only each forecast's current version and its explicit review
date in the interval, excluding resolved or superseded work. A forecast horizon
does not replace a review date. At most 1,000 accessible forecasts are inspected;
larger sets disclose that the count is partial. Alert and job counts are SQL
aggregates without a notification-bell display limit.

Each recipient has one durable intent per actual local calendar day, including
empty periods. Empty periods send no email. A repeated DST hour uses its first
occurrence; a missing hour uses the first valid local time after the gap. An
outage creates one current digest covering the saved gap instead of backfilling
one email for every missed day. Intent creation and cursor advancement commit
together. A time-zone change cannot produce a second intent for a local date
already recorded. SMTP retry and uncertainty rules above apply to digests too.

Opt-out permanently cancels pending windows and fences an in-progress attempt
as uncertain because a relay might already have accepted it. Re-enabling starts
a new interval at that opt-in and never revives the cancelled windows.

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
the offline suite. Daily digest checks include DST boundaries, complete SQL
counts, membership revocation, opt-out/re-enable, empty intervals and competing
SQLite schedulers and senders. Per-rule registered destinations remain separate
delivery work. [Browser push](WEB_PUSH.md) has separate per-device controls and
does not depend on the email preference.

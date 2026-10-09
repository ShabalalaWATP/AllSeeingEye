# Alert rule notification routing

Open **Warning**, save an indicator, then select **Notifications** beside that
rule. In-app storage and streaming always remain enabled. Email and a registered
webhook are independent optional channels. No migration enables either one.

## Automatic reports

When a rule has a report template, its alert and report request are stored in the
same transaction. Evaluation continues without waiting for model calls. A separate
admission worker checks up to eight requests every minute and submits them to the
existing durable report queue. It uses the rule owner's current personal or team
permissions and the usual report allowance and capacity controls. Full capacity
defers admission for five minutes; requests still waiting after 24 hours expire.
The report interval stays anchored to the alert's firing time while it waits.
Its exact minute window, country set, category, keyword, severity and rectangle
predicates are retained with the rule revision. The rectangle takes precedence
over countries, as in alert matching. Reports use the alert's at most 20 cited
events frozen at firing, including original text and source provenance. The full
match count stays separate from this bounded sample; larger populations receive
an explicit evidence-sample finding. Changes or eviction in the live store cannot
replace the frozen evidence. Automatic reports support at most eight valid ISO
country codes; exact-shape rules continue to support alerts only.

The alert shows pending, queued, running, paused, failed or completed progress,
including a link to the report job when one exists. The warning list refreshes
while visible. Configuration or admission failures remain visible on the alert.
Pausing, editing or removing the rule, or removing its owner's workspace access,
prevents further report work and publication. Calls already released to a provider
cannot be recalled. Interrupted paid work retains its reservations and requires
explicit resume through the report progress page; restarting the server does not
automatically replay it. Discarding job progress leaves the alert's report request
terminal and cannot cause a fresh automatic submission.

Migration 0090 adds nullable intent and job-link fields to alerts. Historical alerts
do not enqueue reports after upgrade. Apply the migration before starting the new
application workers. Preserve the additive schema on application rollback; downgrade
refuses to remove retained alert report history. Migration 0091 adds the bounded
evidence snapshot. Old pending requests without a snapshot become failed with
`evidence_unavailable`; old queued jobs without their exact origin cannot execute
or resume. There is no attempt to reconstruct a historical firing from current
live events. Both migrations preserve existing alerts and completed reports.

Alert reports can resume through their durable job while its rule remains current.
Manual regeneration is explicitly rejected because it would recollect evidence.
Create a standalone report for a fresh assessment. Before rolling application code
back to a version without frozen alert snapshots, stop admission and drain or cancel
pending alert work. Retaining the schema alone cannot make an older worker honour
these exact scope constraints.

The report selector offers products whose required inputs the rule can retain.
Country briefs need exactly one country. Ask the Eye and area briefs need a linked
collection plan with a question; its authorised question is retained in the queued
job. Conflict and disaster products require tracker inputs that alert rules do not
store, so use those products as standalone reports. A linked report plan must have
an available area in the same workspace and cannot use an exact polygon.

Saving or resuming a rule rejects missing report prerequisites with a field-specific
repair message. An old incompatible selection stays visible while editing: choose
a compatible product, repair its inputs, or select No report. It can also be paused
without replacing the saved selection. Existing failures remain in alert history;
repairing a rule applies to later firings. A configured model and current workspace
access are still checked at report admission and execution.

Personal rule owners and administrators can manage personal routes. Team routes
require a current manager of the active team or an administrator. Merely reading
a team rule, or creating it as a regular team member, does not authorise external
exports. Personal destinations must belong to the rule owner; team destinations
must belong to the same team, including when an administrator configures them.

## Email

**Email me when this rule fires** uses the account of the person who last saved
the route. Saving a route switches its email recipient to your own account.
There is no arbitrary-address field or implicit team mailing list. Enable the
account email preference and verify the account address under Account, Security
first. Messages use generic labels by default. Rule and alert titles require the
account-level name disclosure opt-in. Messages contain no event summaries.

Turning off account email cancels pending rule mail in the same transaction.
Re-enabling it does not revive old cancelled intents. Revocation during an
already released external call cannot recall a message.

## Registered webhooks

Register a named HTTPS endpoint in the rule's personal or team workspace, then
select it and save routing. Up to 20 active destinations are allowed per workspace.
The URL is encrypted at rest, excluded from read responses and object diagnostic
representations, and never put in audit details or HTTP client diagnostics. Treat
capability tokens in paths and queries as credentials. Removing a destination
disables it; queued delivery rechecks that status before sending.

Every send validates public DNS addresses, pins the checked address, preserves
the original TLS hostname and certificate verification, ignores environment
proxies and never follows redirects. The JSON contains the rule name, title,
summary, countries, event IDs, counts, threshold and firing time. A receiver can
retain that data after the destination is removed. Choose endpoints accordingly.

## Installation-wide copy

`ASE_ALERT_WEBHOOK_URL` remains an operator-controlled **separate copy of every
personal and team indicator firing**. Rule choices and account opt-outs do not
disable it. Both the rule form and routing panel disclose when it is configured;
the capability endpoint never reveals its URL. The environment template explains
the exported data before an operator enables the setting. With no installation
URL, explicitly selected per-rule destinations remain independent.

The installation copy now uses the durable outbox rather than a second immediate
POST. Matching and cooldown logic still stores and streams every alert. A rule
counts only evidence its earlier alerts in the same window have not already cited,
so it fires again only on new evidence rather than on every cooldown.

## Delivery and operations

An alert and its unique per-channel destination intents commit together. Delivery
occurs afterwards. Each worker processes at most 25 intents per tick and waits
30 seconds between ticks. Each intent has at most three attempts. Known rejection
retries after five minutes times the attempt number; unavailable SMTP waits
15 minutes. Webhook answers 408, 502, 503 and 504 count as known rejections and
retry on the same schedule. A lost response, any other server error or an
interrupted claim is conservatively `uncertain` and never automatically retried. A claim older than two minutes is
recovered as uncertain. Idempotency-Key carries the alert ID for receivers that
support it; exactly-once delivery is not promised.

Immediately before network I/O the worker rechecks the rule's existence, enabled
state and original personal/team scope; the rule owner's active account and
membership; the routing revision and current configuring actor's export authority;
and the account email opt-in/verification or destination's active state, scope
and registrar's export authority. Failed checks cancel the intent using a fixed
reason code. Locks are released before outbound I/O. Another channel's transport
failure cannot remove the alert or prevent subsequent channel processing.

Inspect `alert_notification_outbox` for `pending`, `sending`, `sent`, `unavailable`,
`cancelled`, `failed` or `uncertain`. `sent` records transport acceptance only.
Do not reset uncertain rows without independent receiver evidence. There is no
manual resend UI. Alert retention cascades removal of its outbox records.

Migration 0072 adds destinations, routes and outbox tables without enrolling
existing users. Its downgrade removes those new settings and delivery history;
normal release rollback should preserve the additive tables.

KAN-88's replacement rule editor is outside this ticket. Its integration should
keep the installation disclosure visible and open this panel after a saved rule
has an ID, preserving the same API and export-authority checks.

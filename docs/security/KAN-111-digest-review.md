# KAN-111 daily digest boundary review

The account owns its opt-in and its confirmed address. The recipient cannot
provide an arbitrary destination. API saves require the current session fence
and administration guard; the worker rebuilds current account, active membership,
email confirmation and opt-in immediately before preparing count-only content.
Administrator inspection privileges are explicitly removed from the projection.

Digest intents store IDs, schedule and time windows, not report material or email
addresses. A unique recipient/local-day key and conditional claim protect against
competing workers. Window admission and cursor advancement share a transaction.
Network work happens after database locks are released. Cancellation or ambiguous
SMTP acceptance never causes automatic replay; expired leases become uncertain.

Opt-out cancels pending/unavailable windows and marks in-progress work uncertain,
which also fences a prepared-but-not-yet-authorised claim. A later opt-in cannot
revive old windows. Content is recounted from current retained records and active
scope. The forecast projection deliberately caps work at 1,000 ledgers and
discloses partial counts; alert/job totals do not inherit UI pagination limits.

Validation covers local DST gaps/folds, half-open boundaries, empty periods,
outages, SQL totals exceeding bell limits, terminal job statuses, administrator
scope, revoked membership, opt-out/re-enable, API validation and independent SQLite
connections competing to admit and send one window. The optional PostgreSQL race
case remains skipped without an isolated database. Synthetic SMTP behaviour uses
the KAN-110 sender contract. No real email was sent and no delivery credentials
were configured. Independent review and operator relay acceptance remain release
checks; a relay acceptance response does not establish inbox delivery.

## Acceptance clarification, 2 October 2026

The preceding text records the original review checkpoint. KAN-111 requests a
manual SMTP check **when configured**; KAN-110 likewise makes its relay check
conditional on available operator configuration. These checks remain unperformed.
No implementation credentials were configured, but current installation SMTP
availability has not been established, so it must not be described as absent.
The earlier release-check wording does not make this conditional validation an
unconditional Jira blocker. Later PostgreSQL and independent review evidence is
recorded in the [final integration review](../reviews/2026-10-01-final-notification-integration.md).

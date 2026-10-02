# KAN-112 rule notification routing

Base: notification checkpoint `fcbc388f`. Implementation branch:
`codex/KAN-112-rule-routing`. The parent coordinates publication and integration.
No real messages or endpoint registrations were activated.

## Delivered behaviour

- Saved rules expose an additive notification panel. In-app storage stays on;
  email to the saving actor and one registered scoped webhook are optional.
- Personal ownership and active-team management govern external export. Merely
  reading or creating a team rule as a regular member does not grant export.
- Destination URLs are encrypted, absent from read contracts and audit details,
  hidden from dataclass representations and protected from HTTPX/httpcore logs.
  Public-address validation, DNS pinning, verified original-host TLS and no
  redirects apply on every send. Environment proxies are disabled.
- Alert insertion and unique delivery intents share a transaction. Current
  account, rule, team, routing and endpoint authority is checked before dispatch.
  Account email opt-out eagerly cancels/fences queued mail, including after a
  later opt-in. Claims and terminal outcomes are fenced by lease token.
- Dispatch has a 25-intent tick bound, a 30-second pause and three-attempt limit.
  Unknown acceptance is terminal `uncertain`. Channel failure leaves the alert
  stored and allows remaining eligible channels to continue.
- The operator installation webhook is a separate durable copy of every
  personal/team indicator firing. The old immediate notifier is disabled to
  avoid a second POST. The rule form, panel and environment template explain the
  copy and its payload. Matching and cooldown remain unchanged.
- Migration 0072, predecessor 0071, adds three tables without enrolling users.
  Generated OpenAPI and TypeScript contracts match the new HTTP endpoints.

## Verification

- Acceptance/integration command covering routing API, delivery, revocation,
  migration, transport, original warning routes, TLS and lifecycle: **67 passed**.
- Broader warning scope, admission, timing, notification preferences, delivery,
  scope and concurrency checks, with routing API/delivery: **94 passed, 1 skipped**.
  The skipped PostgreSQL case had no disposable database configured.
- After adding competing-claim and production factory wiring coverage, the final
  routing delivery file: **11 passed**. Two competing SQLite stores claim only
  one intent; stale completions cannot rewrite terminal state; the configured
  installation copy sends once from the worker and respects the usual cooldown.
- All warning frontend tests: **16 passed**, including four new routing tests.
  These use the real route table and mocked HTTP endpoints. No screenshot or
  browser-device acceptance claim is made.
- Frontend typecheck, targeted ESLint/Prettier and production build: passed with
  bundled Node 24.19.0. Existing large-bundle warnings remain.
- Ruff source/changed-test checks and formatting: passed. Mypy: **1,402 source
  files passed**. Import linter: **3 contracts kept**. Bandit: passed with existing
  unrelated redundant suppression warnings. File-length and diff checks: passed.
- SQLite migration test runs 0071 to 0072 and downgrade on a disposable file,
  checks empty new tables, encrypted column and uniqueness metadata.
- All transports in tests are synthetic, except the existing owned loopback TLS
  handshake test. No public endpoint or SMTP relay was contacted. Coverage was
  not measured for these focused runs; repository-wide CI remains required.

## Independent security review

The separate security-operations implementation agent reviewed KAN-112 read-only.
Their independent HTTPX probe found URL capability tokens in HTTPX INFO logs.
The repair wraps the whole send path in task-local `protect_http_logs()`, uses
fixed refusal reasons and disables environment proxy selection. The reviewer
re-ran an independent probe and confirmed secret paths/queries are suppressed
while concurrent unprotected requests still log, with pinned address and original
Host/SNI preserved. Committed regressions exercise success, lost response and
concurrent public request diagnostics. No further actionable export-authority or
lease-fencing issue was reported in that review. This is a scoped code review,
not a full repository security audit.

## Integration requirements

- Preserve the existing notification owner's KAN-111/113 work. Add the
  `cancel_alert_email` hook alongside their edition/digest opt-out cancellations;
  keep the additive model/router/lifecycle registrations and their workers.
- The rule worker uses its own claim types, so KAN-111's generic delivery-port
  rename does not require changing them. It reuses `notification_sender`.
- Preserve forecast changes to alert pruning and repositories. This ticket's
  warning-store hook is limited to constructor configuration and `add_alert`.
- Reconcile the explicit Alembic chain with other stacked migrations. Keep
  0072 after the notification 0071 predecessor, regardless of numeric ordering.
- **Required before release:** add
  `alert_webhook_destinations.url_encrypted` to the security predecessor's
  `encryption_rotation.py` column inventory and its inventory regression. That
  module does not exist in this standalone notification checkpoint, so importing
  it here would break the isolated branch. The parent has the exact new column.
- KAN-88 is outside this Codex ticket batch. Its replacement rule editor should
  retain the disclosure and reuse this saved-rule panel and HTTP contracts.
- PostgreSQL competing-worker/migration acceptance, real relay/receiver checks
  with synthetic content and full combined CI remain release verification.

Operational behaviour and API/UI use are documented in `docs/ALERT_ROUTING.md`.

## Combined notification checkpoint

Integrated into the KAN-110/111/113/141 notification branch after `78a6dc9b`.
The master email preference now permanently cancels pending edition, digest and
rule mail in one transaction, fences claimed sends as uncertain and disables the
digest preference. A two-case integration regression checks an off/on sequence
both before and after claims across all three outboxes.

- Combined focused backend checks: **134 passed, 3 skipped**. The skipped cases
  require a disposable PostgreSQL database. The two new integration cases passed
  after correcting fixture login order before enabling email MFA.
- Selected warning, notification account, browser push and auth frontend checks:
  **48 passed**. TypeScript, changed-file ESLint/Prettier, Ruff and formatting,
  mypy (**1,424 source files**) and all three import contracts passed.
- Contracts were regenerated from the combined API. SQLite migration and CLI
  checks passed. Alembic reports one head, `0074`, with the standalone chain
  `0066 -> 0071 -> 0072 -> 0074` pending the parent's serial integration.
- The separate email, digest, rule and browser push workers and revocation hooks
  remain registered. No live SMTP, webhook or browser provider delivery occurred.

Full combined CI, PostgreSQL acceptance, synthetic live-device checks and the
two encrypted-column rotation inventory additions remain with parent integration.

## Acceptance clarification, 2 October 2026

The preceding sections retain their original checkpoint evidence. KAN-112 requires
permission, destination, revocation, duplicate-intent and fake-channel failure tests;
it does not require a live relay or webhook receiver check. Those checks remain
useful deployment recommendations, not additional Jira closure criteria. KAN-110's
manual email check is conditional on available operator configuration, whose
current installation state has not been established. Later PostgreSQL, rotation
inventory and independent review evidence is recorded in the
[final integration review](2026-10-01-final-notification-integration.md).

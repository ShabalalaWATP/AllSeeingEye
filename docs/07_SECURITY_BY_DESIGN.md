# Security by Design

Status: implementation guidance updated for Phase 5 and Phase 6, 6 September
2026. These controls describe the current code, with deployment and verification
limits called out below. They do not establish OWASP ASVS level 2 conformance or
public-exposure readiness. The detailed review and remaining gates are in
[PHASE6_ASVS_REVIEW.md](security/PHASE6_ASVS_REVIEW.md).

## 1. Threat model

Assets are accounts and sessions, administrator TOTP, model/feed credentials,
saved reports and frozen evidence, configuration, the host machine and its
outbound network access. Relevant actors include anonymous callers, authenticated
users exceeding their role, hostile feed publishers, malicious or misconfigured
model endpoints and compromised dependencies.

Primary risks are broken authentication and authorisation, prompt injection,
SSRF, browser script injection, credential disclosure, excessive resource use
and supply-chain compromise. The intended operating boundary is one controlled
home machine or LAN/Tailscale deployment with one API process. A different
exposure or multi-worker topology needs a new review.

## 2. Implemented controls

### Identity and sessions

- Argon2id hashes passwords; policy includes an offline common-password deny
  list. Account requests require administrator approval.
- Access tokens are short-lived JWTs held in browser memory. Refresh tokens are
  opaque, stored as hashes and rotated through an HttpOnly cookie. CSRF checks
  protect cookie-authenticated refresh/logout operations.
- `CurrentUser` verifies the access token and reloads the user's active state and
  current role from the database for every protected HTTP request. Deactivation
  and demotion therefore affect the next request even if its access JWT has not
  expired. A signed token alone is not the source of current permissions.
- Login and account-recovery endpoints have bounded rate limits and account
  lockout. Password activation/reset tokens are hashed, time-limited and single
  use. Responses avoid exposing account existence. Email delivery is not
  configured; administrators can issue activation/reset links locally.
- Optional administrator TOTP is implemented, including password-authorised
  enrolment, confirmation, encrypted secrets, expiring enrolment state and code
  replay protection. Enabling/removing TOTP revokes refresh sessions. Host-only
  recovery uses `ase recover-admin-totp`; there is no HTTP recovery bypass.
- Token rotation, reset consumption and TOTP transitions have deterministic
  tests. Concurrent refresh-family invalidation and PostgreSQL execution need
  the separate verification recorded in the Phase 6 review; unit tests alone
  do not establish every lifecycle race property.
- Authentication and administrative actions write audit records. This is an
  application audit log, not a tamper-proof external audit service.

### Authorisation

- `user` and `admin` roles are checked at protected boundaries. Administrator
  operations require the current administrator role.
- Reports and collection plans are shared reads for active authenticated users.
  Report exports, version comparisons and semantic search follow the same read
  policy. The current product does not promise owner-private report libraries.
- Report and plan mutations require the owner or an administrator in application
  use cases. Object identifiers do not grant permission to mutate another user's
  records. Similar feature-specific checks protect areas, indicators and
  schedules; do not infer a different read policy from ownership alone.
- SSE checks current identity on connection and expires no later than the
  presented token. It has per-user/global admission bounds. Already-open streams
  do not re-read account state for each message; reconnects repeat authentication.

### External feeds and content

- Feed HTTP requests use public-host checks and DNS pinning to reject private,
  loopback, link-local and metadata destinations. Redirect hops are checked by
  the guarded feed client. Administrator-selected model endpoints use the
  separate trust boundary below.
- Feed responses have per-request byte limits and timeouts. XML uses
  `defusedxml`; text is stripped of markup and bounded before it enters events.
  Parsed values and coordinates are constrained by domain/schema validation.
- Dynamic Mastodon instances and watchlist requests use the guarded feed path.
  Google News link resolution is deferred until report citation processing; it
  does not fetch every article in a live feed or create an article archive.
- The React report reader, social board, evidence annex and version comparison
  render structured text nodes. Links must pass HTTP(S) URL checks. There is no
  browser Markdown-to-HTML or DOMPurify rendering path in the implementation.
- Optional Wayback archiving sends cited URLs to the Internet Archive after
  report production; `ASE_ARCHIVE_ENABLED=false` disables that step. Optional
  webhook routing requires a public destination and sends one bounded alert
  notification without retries. Separate archive, tile and webhook adapter
  review remains a deployment gate; the feed guard is not proof that every
  outbound adapter has identical redirect and buffering behaviour.

### Model boundary

- Only administrators configure model profiles. Private/loopback endpoints are
  allowed deliberately for self-hosted models. The administrator's endpoint
  choice is the trust boundary; applying the public-feed policy would prevent
  that supported local workflow.
- Model keys are decrypted server-side and sent in an Authorization header.
  Redirects are disabled. Chat and embedding adapters request identity encoding
  and refuse compressed responses before consuming response content.
- Chat responses stream under a 4 MiB cap and a 120-second default overall
  deadline, including admission. A shared semaphore admits two chat requests at
  once. Chat JSON structure is checked with a depth bound.
- Embedding responses stream under a 2 MiB cap and a 30-second endpoint deadline,
  with an application deadline around the call. Queries/indexing use a shared
  process-local lock and per-user/global hourly model-call limits. Vectors must
  contain finite numeric values, non-zero magnitude and at most 4,096 dimensions.
- Gateway error messages contain safe status/context only. They never include
  provider response excerpts, credentials, request headers or secret-bearing
  connection details in report findings or usage records.
- Evidence is delimited as untrusted data. Instruction-like material is screened
  out before selection; models receive no side-effecting tools. Structured
  assessment output is validated against doctrine, citation labels and the
  information-quality ceiling. Failed validation retries once and then marks
  the assessment for review instead of claiming success.
- Saved versions retain evidence, assessment, findings, analysis, model and
  usage metadata. Browser and document exports preserve the machine-generated
  assessment warning. They do not imply that an analyst has reviewed the result.

### Durable data and secrets

- Raw live events stay in the bounded in-memory store and are excluded from
  database writes and backups. Saved report evidence is deliberately durable;
  small hourly activity counts support baselines without preserving event rows.
- Semantic search indexes already saved report assessment text, with one JSON
  vector per indexed report and a latest-1,000-report bound. No pgvector service
  or raw-event semantic archive is used. See
  [ADR 0008](adr/0008-bounded-report-search.md).
- Model credentials and administrator TOTP secrets use Fernet under
  `ASE_ENCRYPTION_KEY`. Existing keys are never read back through profile APIs;
  new TOTP enrolment material is returned once to the authorised enrolment flow.
  Preserve the encryption key separately for recovery.
- Real `.env` files are excluded from git. Structured logging has secret
  redaction, and model/driver errors must remain safe before they reach logs.
  Reports and frozen evidence can contain personal information present in public
  sources; they need the same private storage care as account records.

### Transport, runtime and recovery

- Development uses a same-origin Vite API proxy. Compose serves HTTPS through
  Caddy's internal CA, with the API and database ports unpublished.
- Caddy applies CSP, frame restrictions, MIME sniffing protection and referrer/
  permission restrictions. Script sources are restricted to self; inline styles
  and blob workers are specifically allowed for MapLibre. API responses have
  their own restrictive headers. HSTS remains disabled for the default local
  certificate setup and must be verified for an actual public deployment.
- The API container runs as a non-root user with a read-only root filesystem,
  temporary `/tmp` and `no-new-privileges`. Do not generalise these settings to
  every service: PostgreSQL and Caddy have their own image/volume requirements.
- The live store enforces category/item limits and an estimated memory budget.
  Request body limits, stream admission, model timeouts and bounded search reduce
  resource exposure. Process memory still requires representative-load testing.
- [Backup/restore scripts](BACKUP_RESTORE.md) create consistent SQLite snapshots
  or Compose PostgreSQL dumps, verify a strict hash manifest, refuse unsafe
  paths, and restore only into new destinations. Actual `.env` inclusion is
  explicit. No nightly schedule, automatic pruning or destructive restore is
  installed. The offline SQLite drill is real; PostgreSQL command tests are
  mocked and a live recovery drill remains outstanding.

### Supply chain

Lockfiles, pinned CI actions and repository checks cover linting, type checking,
tests, dependency audits, secret detection, SAST and container scanning. These
are configured controls: no GitHub CI result has been observed because the
repository has no configured remote. Record actual local results in the current
implementation plan and do not describe workflow definitions as passing scans.

## 3. Residual assumptions and exposure gates

The [Phase 6 review](security/PHASE6_ASVS_REVIEW.md) is the detailed record of
findings, fixes and remaining evidence. The principal operational gates are:

1. Keep one API process. Rate limits, search coordination and stream/model
   admission are in-process. Keep API/database ports private and narrow
   forwarded-header trust if the Compose network boundary changes.
2. Retain the verified PostgreSQL session-race regressions and define access-token
   revocation/recovery expectations. Ordinary requests re-check active state and
   role, but logout does not add a universal access-JWT deny list, and a running
   SSE connection lasts until its deadline.
3. Account lockout can be used to deny access to a known account. This remains a
   documented LAN trade-off, not an acceptable default for unreviewed public
   exposure. Host access also gives access to `.env`, volumes and recovery tools.
4. Complete applicable ASVS level 2 requirements and an authenticated baseline
   scan of an owned local/staging deployment. Verify actual TLS, cookies, CSP,
   CORS, body limits, proxy trust and HSTS. No production scan is implied.
5. Complete independent outbound-adapter checks and retain final dependency,
   secret, SAST and image scan evidence. A synthetic PostgreSQL recovery drill
   passed across all 19 migrated tables; repeat it with the operator's backups.
   Hashes detect damage; they do not authenticate a replaced backup manifest.
6. Exercise a configured real model and representative load. Define operational
   log/audit/usage retention, storage permissions, backup scheduling and alert
   handling for the deployed host. These are not installed by the scripts.

No remaining gate authorises production changes, credential rotation, external
disclosure, scheduled jobs or public exposure without a separate operator action.

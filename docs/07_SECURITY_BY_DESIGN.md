# Security by Design

Status: implementation guidance updated for identity and team isolation, 6 September
2026. These controls describe the current code, with deployment and verification
limits called out below. They do not establish OWASP ASVS level 2 conformance or
public-exposure readiness. The detailed review and remaining gates are in
[PHASE6_ASVS_REVIEW.md](security/PHASE6_ASVS_REVIEW.md). The broader current
delivery audit is tracked in [the improvement plan](MASTER_FIX_IMPROVEMENT_PLAN.md).

## 1. Threat model

Assets are accounts and sessions, administrator TOTP, model/feed credentials,
saved reports and frozen evidence, configuration, the host machine and its
outbound network access. Relevant actors include anonymous callers, authenticated
users crossing personal/team boundaries or exceeding their role, hostile feed publishers, malicious or misconfigured
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
  current role from the database for every protected HTTP request. It also
  requires a live refresh family and matching account security version. Logout
  invalidates that family's access tokens; password, TOTP and account role/status
  changes invalidate the affected sessions even before access JWT expiry.
  A signed token alone is not the source of current permissions.
- JWTs require `sid` (family id) and `sv` (security version). Old access JWTs
  without them are refused after upgrade. Existing valid refresh cookies may
  rotate into the new token format; expired/revoked cookies require sign-in.
- Login and account-recovery endpoints have bounded rate limits and account
  lockout. Password activation/reset tokens are hashed, time-limited and single
  use. Responses avoid exposing account existence. Email delivery is not
  configured; administrators can issue activation/reset links locally.
- Optional administrator TOTP is implemented, including password-authorised
  enrolment, confirmation, encrypted secrets, expiring enrolment state and code
  replay protection. Enabling/removing TOTP revokes sessions and increments the
  security version. Host-only
  recovery uses `ase recover-admin-totp`; there is no HTTP recovery bypass.
- Token claims, family revocation, single-use token consumption and account/TOTP
  transitions have deterministic regressions. A shared administration guard and
  ordered account locks recheck the acting administrator during role/status
  changes. Self-modification is forbidden, so two administrators cannot race to
  remove every active administrator through the supported API. Test evidence
  remains specific to the recorded database and scenarios; it is not a proof of
  every possible lifecycle race.
- Authentication and administrative actions write audit records. This is an
  application audit log, not a tamper-proof external audit service.

### Authorisation

- Global roles are `user`, `manager` and `admin`. Administrator operations require
  the current administrator role. Manager authority additionally requires a
  `manager` membership designation in the specific team. It never grants global
  account, credential, reset-link or directory access.
- The dedicated administration shell is guarded before its pages mount; research
  navigation exposes its entry only to authenticated, active administrators. This
  visual separation complements server permission checks, rather than replacing
  them. Activation and reset-link responses revalidate the original session and
  current administrator role after the authorised transaction and any email
  delivery, before releasing a secret-bearing result. Revocation blocks the
  response without undoing an already committed approval.
- Personal roots (`team_id = null`) are readable by their creator and
  administrators. Team roots are readable by current members and administrators.
  This policy covers reports and historical versions, exports, comparisons,
  semantic search, AOIs, plans, indicators, schedules and alerts. Public source
  events and source health remain shared. Identifiers outside the caller's read
  scope return 404, including attempted mutations, to avoid existence disclosure.
- Current team members may manage their own contributions; designated managers
  may manage other contributions in that team. Linked records must share the same
  personal owner or team, even when an administrator makes the request. Ordinary
  content editing cannot transfer a record to another scope.
- Alert acknowledgement is shared triage: any current member of an active team
  may acknowledge its alerts. Personal alerts remain owner/admin-only, and
  archived teams retain the ordinary read-only rule.
- Archived teams retain read access, while ordinary operational writes stop.
  Administrators retain a deliberate manual operational override. Membership
  edits require reactivation. Background collection/reporting requires an active
  owner and active team membership even for an administrator-owned job.
- The shared `AccessPolicy` reloads current identity and memberships. Repositories
  apply its SQL visibility predicate before limits and counts. Mutations take the
  administration guard before account locks and rechecks, serialising them with
  membership, archive and account transitions. No-op updates provide real locking
  on both SQLite and PostgreSQL; SQLite `FOR UPDATE` alone is not relied upon.
- Outbound model work does not retain these database locks. Report generation and
  embedding writes rebuild authority after the call before persisting results.
  Searches re-read visible reports after embedding the query. Background stores
  recheck eligibility before saving alerts, run outcomes and report links.
- PDF/DOCX downloads recheck current access after rendering and before releasing
  bytes. Private operational routes carry `Cache-Control: no-store`; downloads
  preserve `private, no-store`. Previously downloaded copies cannot be recalled.
- SSE revalidates in a fresh transaction before delivery and at least every
  15 seconds while idle, subject to service scheduling. It filters alert payloads
  by scope, emits `access.changed` when team access changes and closes revoked or
  expired sessions. The client invalidates scoped data/selections on access
  changes. Admission remains bounded per user and globally.
- Migration `0014` does not invent shared teams or assign old records to one.
  Existing roots stay personal; alerts inherit surviving indicator ownership and
  orphan alerts remain administrator-only. `legacy_scope_conflict` audit entries
  inventory missing/cross-owner links without copying their content. Historical
  links and evidence remain intact, while incompatible new operations are denied.
  See [ADR 0010](adr/0010-teams-and-access.md).

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
- Private plan terms used for enabled Google News collection are sent to Google;
  their resulting public articles remain in the shared live picture. Plan/PIR
  identifiers are not attached to public events. The social board reveals private
  terms only to their personal owner, current team members or administrators.
  Revoked/inactive owners and archived teams stop supplying background terms.
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
- Semantic search indexes already saved assessment text, with one JSON vector per
  indexed report and a shared limit of 1,000 stored vectors. Capacity is checked
  before embedding calls; a full index refuses new slots without evicting other
  teams' entries. Global maintenance prunes orphaned/superseded versions, not
  everything outside one caller's scope. Searches/counts use up to the caller's
  latest 1,000 visible reports. No pgvector service or raw-event archive is used. See
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
  installed. A synthetic SQLite/PostgreSQL 17 drill through migration `0011`
  verified the 19 then-existing tables and recovery of encrypted values. It is
  separate from recovery of the operator's backups and the new scope migrations.

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
2. Retain session, account-transition, team revocation and background-work
   regressions on SQLite and PostgreSQL. Back up the actual database, then apply
   migrations explicitly before running the new code. No operator database or
   real `.env` was changed during development verification. Review the migration's
   legacy conflict audit entries and repair incompatible links before using
   affected collection workflows.
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

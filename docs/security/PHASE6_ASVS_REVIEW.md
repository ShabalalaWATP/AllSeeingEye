# Phase 6 security review against ASVS 5.0

Historical baseline review: `60dff6b`, 6 September 2026. Target: the Phase 6 working tree, including
Phase 5 and Phase 6. Deployment assumption: private, single-process, self-hosted
LAN application. This is a source review and local test record, not certification,
an assertion that every ASVS requirement passes, or approval for public exposure.

The reference is [OWASP ASVS 5.0.0](https://owasp.org/www-project-application-security-verification-standard/),
using the [versioned English requirements](https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json).
The coordinating agent verified that version and its chapter names. The security
reviewers kept source inspection offline.

The later [improvement security review](IMPROVEMENT_SECURITY_REVIEW.md) supersedes
this baseline's shared-read and access-token-expiry assumptions. Findings below
retain their historical context.

## Method and limits

Codex Security Standard capability preflight returned `ready`: delegation and the
available worker capacity checks passed. The advisory TAC result was `granted`,
level `tac1`. An independent static auditor and a separate architecture reviewer
reviewed the current source; the coordinating security reviewer validated the
findings and ran selected local tests. No remote DAST, production scan, live
credential probe or Git-history review was performed.

Coverage is partial at repository level. Review concentrated on authentication,
object mutations, the new translation/social/watchlist/report features, outbound
clients, exports, backups, browser boundaries and deployment configuration.
Search hits and architecture-only reads do not count as fully audited files.
Generated API descriptions, all individual feed parsers, third-party dependency
implementation and every UI component were not exhaustively audited.

Source changed during the review as the implementation team applied fixes. The
findings below describe the defects encountered, with their final verification
status recorded separately. The generated scan report retains that distinction.
Codex Security scan `a2451469-a623-460d-8100-0d8704bebe10` was successfully sealed.
Its workbench report is bound to the launch snapshot and explicitly warns that
the working tree changed while scanning. The remediation checks here describe
the later working tree; the report is not a fresh immutable audit of the final
release tree. Measured scan token usage was unavailable.

## Findings encountered

All five findings were rated **medium** in this deployment. Token races require
possession of a live token; provider findings require a compromised, malicious or
credential-echoing configured upstream. No real credential disclosure was observed.

| ID | Finding and source evidence | Impact and remediation | Verification status |
| --- | --- | --- | --- |
| F1 | Concurrent refresh rotation, CWE-362. `application/auth/refresh.py` checked `revoked_at`, then `adapters/persistence/tokens.py` saved it unconditionally. | Two transactions could issue independent successors without detecting reuse. Atomically consume the unrevoked, unexpired token before issuing its child in the same transaction; a lost claim must revoke the family. | Fixed. Deterministic independent-session races pass. Durable family markers also reject descendants missed by a revocation update; the auth worker ran the PostgreSQL interleaving regression described below. |
| F2 | Concurrent password-token redemption, CWE-367. `application/auth/set_password.py` checked usability, wrote the password, then marked the token used. | Two requests could both succeed and the final password depended on write order. Atomically claim the unused, unexpired token before changing credentials, with rollback covering both operations. | Fixed. Single-winner redemption and transaction rollback regressions pass, retaining activation and inactive-account rules. |
| F3 | Report regeneration omitted object authorisation, CWE-862. `application/reports/generate.py` accepted any shared report UUID and changed its current version/status. | An unrelated signed-in user could change another owner's current report. Require owner or administrator before any model call or version write. | Fixed. API regression confirms a shared reader receives 403 with no version or usage write; the owner passes the ownership guard. Shared reading remains intentional. |
| F4 | Chat response cap followed allocation, CWE-400. `adapters/llm/openai_compatible.py` awaited buffered `post()` before its 4 MiB check. | A hostile provider could exhaust API memory or keep a request alive with periodic data. Stream/count bytes before buffer growth and impose a total deadline. | Fixed. Over-limit and slow streams close promptly; compression is rejected before decoding; two-call admission and queue deadlines are tested. JSON depth and malformed output fail safely. |
| F5 | Provider error bodies entered reports, CWE-209. The chat gateway's excerpt became a `Finding` in `application/reports/drafting.py`, then persisted report/Markdown/usage data. | A provider echo of an API credential could reach ordinary report readers. Return safe categories/status codes without response bodies. | Fixed. Tests inject a synthetic key and verify it is absent from exceptions, persisted report responses and usage. Error bodies are never read. |

Paths in this table are beneath `backend/src/ase/`. The original vulnerable
snippets and source-to-sink reasoning are retained in the generated scan artefacts.

The suggested private-plan disclosure candidate was rejected: collection plans
are explicitly readable by all signed-in users in
`application/direction/plans.py`. Selecting one for a new caller-owned report is
not a private-data boundary crossing. Shared report reading, export and search
are also explicit policy. Shared reading does not grant report mutation rights.

## ASVS control-family evidence matrix

Statuses describe the **listed reviewed controls**, not the whole ASVS chapter:
**verified locally** means inspected source plus relevant passing local tests;
**partial/manual** means source evidence exists but further requirement or runtime
verification remains; **not applicable** means the feature is absent from this
application. Source paths below are relative to the repository root.

| ASVS 5.0 family | Status | Evidence and remaining scope |
| --- | --- | --- |
| V1 Encoding and Sanitization | Verified locally for reviewed exports and feed boundary | `backend/src/ase/application/feeds/pipeline.py` strips tags and bounds text. PDF escapes text with `html.escape(..., quote=False)` in `adapters/reports/pdf.py`; DOCX writes text only. `test_report_documents.py` checks literal hostile markup, absence of external relationships/media and no PDF annotations. The frontend renders structured React text. This does not certify every parser. |
| V2 Validation and Business Logic | Partial/manual | Pydantic request bounds, bounded translation/watchlist budgets and search library/vector limits are explicit. Search uses a shared lock and hourly budgets. `test_report_search.py` covers invalid vectors, stale/deleted versions and call limits. Token single-use and family invalidation have the concurrency evidence below; the full business-rule inventory remains outside this review. |
| V3 Web Frontend Security | Partial/manual | `frontend/src/stores/auth.ts` keeps access tokens in memory; report/diff rendering uses React text. Caddy CSP restricts scripts to self, with documented inline-style/blob-worker allowances for maps. Verify the built SPA under Caddy, headers on error paths, browser storage, cross-origin requests and staged scanner results. Vite is a separate development serving path. |
| V4 API and Web Service | Partial/manual | `api/deps.py` verifies bearer credentials and reloads active users; body middleware counts streamed bytes. Auth cookie endpoints require CSRF. No permissive CORS middleware was found. Validate proxy/header trust and actual deployed request limits in staging. |
| V5 File Handling | Verified locally for exports and local bundle handling | Exports have fixed UUID/version filenames, attachment/no-store headers, bounded document content and two render slots. Backup bundles allow only fixed members, reject traversal/symlinks/junctions, verify hashes and create new destinations exclusively. Export/backup tests passed. The backup worker also completed synthetic SQLite and disposable PostgreSQL 17 CLI restore drills; operator-specific recovery and storage ACL checks remain. |
| V6 Authentication | Partial/manual | Argon2id parameters are explicit in `adapters/security/hasher.py`; password policy uses length and an offline common-password list. TOTP uses PyOTP, encrypted seeds, adjacent-step verification, atomic code consumption, password reauthentication and a host-only recovery command. `test_totp.py` and `test_totp_security.py` passed. TOTP is optional and only offered to administrators; it is not universal MFA. |
| V7 Session Management | Partial/manual | Refresh cookies are HttpOnly, Strict and production-Secure; CSRF comparison is constant-time. Atomic redemption and durable family revocation markers fix F1, including the tested PostgreSQL missed-descendant case. Logout/reset/TOTP changes revoke refresh sessions. Existing access tokens are not individually revoked, and already-running streams end at token expiry. Concurrent new login during credential change and multi-process lifecycle semantics are not established by the family-marker test. |
| V8 Authorization | Partial/manual | Current role and active status are loaded from SQL on each new authenticated request. Admin checks and owner/admin mutations exist in application use cases. Reports/plans are shared reads by policy. F3 adds regeneration authorisation. Verify the complete object/action permission matrix, including every mutation and background owner context. |
| V9 Self-contained Tokens | Partial/manual | `adapters/security/jwt_issuer.py` fixes HS256, requires subject/expiry/type/JTI/issued-at claims and checks application-clock expiry. Tokens are signed with the configured server secret and are not accepted as current role authority. Issuer/audience requirements and deployment-specific key-management expectations still need a full ASVS requirement review. |
| V10 OAuth and OIDC | Not applicable | This application uses its own password/session login and has no OAuth/OIDC client or authorisation-server flow. Reassess if one is added. |
| V11 Cryptography | Partial/manual | Password salts/hashing, opaque tokens, Fernet encryption and TOTP use maintained libraries. LLM credentials and TOTP seeds share `ASE_ENCRYPTION_KEY`; the configured random secret is hashed into a Fernet key. Verify key entropy, storage, recovery access and an operational rotation procedure. No custom encryption primitive was introduced. |
| V12 Secure Communication | Partial/manual | Feed HTTP validates every DNS answer, pins the chosen public address and rechecks redirects. Feed, chat and embedding clients request identity encoding and reject compressed responses before decoding; noncompliant upstreams therefore fail closed. Model private endpoints are intentionally administrator-controlled. Caddy uses an internal CA; HSTS is currently disabled. Archive/webhook/tile clients have separate controls and require their own bounds/redirect review. Verify trusted TLS and network exposure before public use. |
| V13 Configuration | Partial/manual | Production requires a JWT secret; interactive API docs are development-only. API container runs as non-root with read-only root and tmpfs. Compose publishes web ports only. Web/db hardening and pinned image digests are separate deployment work; API declarations do not establish those properties for every container. |
| V14 Data Protection | Partial/manual | LLM keys/TOTP seeds are encrypted in SQL; profile APIs expose only key hints. Search persists bounded report vectors, while live events remain in memory. Backups contain private database state and optionally plaintext `.env`; Windows ACLs are inherited. Verify retention, deletion, backup encryption/access and recovery procedures. |
| V15 Secure Coding and Architecture | Partial/manual | Layered ports/adapters, locked dependencies and declared CI scanners are present. Source review traced trusted configuration to sensitive consumers. F4 corrects chat buffering. The live-store memory figure is an estimate, not measured RSS; performance/load and process concurrency evidence remain separate. No dependency-audit result is inferred from workflow declarations. |
| V16 Security Logging and Error Handling | Partial/manual | Authentication/admin/TOTP events are audited. General logging redacts sensitive field names one level deep, not arbitrary string contents. F5 removes upstream bodies at the gateway boundary. Verify redaction across production logs, retention/access, central monitoring and failure paths; application append-only methods are not database immutability. |
| V17 WebRTC | Not applicable | No WebRTC media/signalling feature exists in the application. Reassess if added. |

## Local checks performed by the security reviewer

The following offline selection passed: **133 tests in 27.86 seconds**, with
coverage disabled for this focused run:

```text
uv run pytest tests/test_totp.py tests/test_totp_security.py
  tests/test_report_documents.py tests/test_report_documents_api.py
  tests/test_report_search.py tests/test_embeddings_gateway.py
  tests/test_google_news_links.py tests/test_backup_restore.py
  tests/test_backup_postgres.py --no-cov -q
```

The displayed command is wrapped for readability; it was executed as one command
from `backend/`. Tests used temporary/local databases and mocked upstream
transports. No full-suite coverage percentage is attributed to this selection.

Additional reviewer checks passed:

- **34 tests in 39.42 seconds**: `test_token_redemption_races.py`,
  `test_refresh_logout.py`, `test_forgot_reset.py`, `test_feed_http.py`.
- **1 test in 3.15 seconds**: `test_report_permissions.py`.
- **67 tests passed, 1 skipped in 32.92 seconds**: `test_token_redemption_races.py`,
  `test_refresh_family_revocation.py`, `test_llm_gateway_security.py`,
  `test_llm_output_security.py`, `test_embeddings_gateway.py`,
  `test_feed_http_bounds.py`. The skipped test requires PostgreSQL; the other
  tests used local SQLite and mocked transports. Each selection used `--no-cov -q`.

These selections overlap, so their counts are not a unique-test total. The auth
worker separately reported **8 targeted tests passing on PostgreSQL 17**. Its
family-revocation test uses a database lock barrier to force a descendant insert
outside the revocation update's snapshot, confirms the descendant remains
unmarked, then confirms its refresh is refused by the durable family marker.
The security reviewer inspected that implementation and test, and ran its SQLite
equivalents. Migration `0011` creates the required marker table.

The backup worker ran actual CLI backup/restore drills using synthetic SQLite and
disposable PostgreSQL 17 databases after migrations through `0011`. Both restored
19 tables with matching logical SHA-256 digests, retained two report versions and
frozen evidence, decrypted the model key and TOTP seed, and retained vectors,
aggregates, audit data and the family marker. The originals were unchanged. The
reviewer inspected the recorded result at
`data/phase6-backup-qa/run-20260906-15440/results.json`; this is temporary local QA
evidence, not a committed production backup or operator recovery drill.

Gitleaks **v8.30.1** scanned the current working tree with a read-only repository
mount, no container network and redacted output: **3.61 MB, no leaks found, exit 0**.
Ignored data, local environment files, dependency/build directories and caches were
excluded. This was not a Git-history scan.

Semgrep **1.162.0** ran offline using the official `p/default` and
`p/security-audit` configurations fetched by the coordinating agent. The first run
examined **449 files with 457 applicable rules**, reported no parsing errors, and
exited **1 with 13 blocking alerts**. Source triage found:

- Five `python37-compatibility-importlib2` alerts: the project requires Python
  3.12 or newer, so Python 3.6 compatibility is not applicable.
- Five `use-defused-xml` alerts: the standard-library imports supply `Element`
  and `ParseError`; all five parsing sites call `defusedxml`'s `safe_fromstring`.
- Two Django SQL alerts on `auth.py`: these are application use-case `execute`
  methods, not database cursors. Repository token queries use SQLAlchemy binds.
- One Django password-validation alert: `SetPasswordUseCase` calls the project
  password validator before hashing and saving.

These are rejected scanner candidates, not new vulnerabilities. Each now has a
narrow preceding-line annotation with its exact rule ID and rationale. The final
verification run passed: **exit 0, zero findings, 457 applicable rules on 449
files, zero parsing errors**. Nineteen files matched Semgrep's default ignore
patterns. The configured rule sets were unchanged; no rules were excluded.
`--no-rewrite-rule-ids` keeps local and CI rule IDs identical, and CI retains
`--error`. The original failed result is retained alongside the final result.

The first reviewer Bandit run returned one low-severity B406 on the PDF escape
import and no medium/high findings. Inspection showed no XML parsing. The team
replaced it with equivalent `html.escape` and the coordinating agent reported a
clean rerun. The coordinating agent also reported clean locked Python and pnpm
dependency audits; the local `ase` package was skipped by pip-audit because it is
not a PyPI distribution. Full-suite, lint, type and build results remain the
coordinating implementation agent's separate evidence.

The coordinating agent's initial API-image Trivy scan exited 1 with two HIGH
alerts: `GHSA-6v7p-g79w-8964` for msgpack 1.1.2 and `CVE-2025-47273` for setuptools
70.3.0. The agent traced both to the base image's pip 26.2.1 vendored packages,
outside the application virtual environment. `backend/Dockerfile` now removes
unused base pip and build caches after synchronising the locked runtime
environment. The security reviewer inspected that change. After this source
review was sealed, the coordinating agent rebuilt the actual API Dockerfile and
verified the final image with Trivy: **exit 0, no HIGH/CRITICAL findings with the
CI `ignore-unfixed` policy**. The report identifies image
`sha256:601ded7571d588715e8dc09df922eb9912bc4199cda18b76c762de394de8729f`.
An isolated read-only, non-root, network-disabled container also passed migrations
and imports of the application and document/TOTP dependencies. Local evidence is
in `data/phase6-verification/trivy-api-final.json`.

The initial web image had **38 HIGH and one CRITICAL** finding in Alpine packages
and the official Caddy binary's Go dependencies. The final web Dockerfile builds
the same Caddy 2.11.4 standard release with Go 1.26.6 and a checksum-verified,
locked dependency graph, then updates the inherited Alpine packages. The build
retains all **132 standard modules**, the same adapted Caddy configuration and
`cap_net_bind_service=ep`. Configuration validation and local HTTPS checks passed
for static content, compression, SPA fallback, security headers and API routing
(health 200 and unauthenticated `/api/me` 401). API routing used read-only GETs
against the existing local API; the temporary proxy container was removed.

Final web Trivy verification passed: **exit 0, no HIGH/CRITICAL findings without
ignoring unfixed findings**. The exact scanned image is
`sha256:dca511366f8cb6edf55794a26beda6a0eb9c40f279adddb35eb11c61d02116c6`.
The initial and final scans used the same database, updated at
`2026-09-05T19:14:02Z`. Local evidence is retained as
`data/phase6-verification/trivy-web-before-caddy-rebuild.json`,
`trivy-web-final.json`, `caddy-build-validation.json` and
`caddy-smoke-validation.json`. The [Caddy build notes](../../infra/caddy-build/README.md)
document provenance and maintenance. These results cover the final API and web
images at the recorded database snapshot, not every possible vulnerability or
the PostgreSQL/PostGIS deployment image. Rebuild and rescan release artefacts.

## Residual LAN assumptions and public-exposure gates

1. Keep one API process and keep API/database ports unpublished. In-memory rate
   limits, live store, search lock and export slots are process-local. Narrow
   forwarded-header trust if the Compose network boundary changes.
2. Apply migration `0011` before running the updated authentication code. Retain
   the PostgreSQL interleaving regression in CI. Define access-token revocation
   expectations explicitly: family invalidation prevents subsequent refreshes,
   while already-issued access tokens can remain usable until their short expiry.
3. Complete an explicit ASVS level 2 requirement checklist for applicable controls,
   including authentication recovery and access-token revocation expectations.
   Optional administrator TOTP and a family-level matrix do not establish level 2
   conformance. Account-lockout denial of service remains a recorded LAN trade-off.
4. Use a trusted HTTPS deployment and verify Secure cookies, CSP, CORS, proxy
   headers, request limits and HSTS under the actual Caddy configuration. Run an
   authenticated OWASP ZAP baseline against an owned local/staging stack and
   resolve findings before any exposure beyond the LAN. No production scan is
   authorised by this document.
5. Validate all remaining outbound adapters independently. Fixed initial archive
   hosts do not constrain followed redirect destinations. Archive availability,
   webhook and tile response buffering differ from feed/embedding streaming.
   No user-controlled archive redirect exploit was established in this review.
   Chat admission now limits concurrent upstream calls to two per gateway process;
   optional tile-service request budgets still need operational verification.
6. Retain the executed dependency, secret-scan, SAST and final API/web image scan
   results. Repeat release checks for the deployed artefacts, including the
   PostgreSQL/PostGIS image. The local PostgreSQL tests passed, but the hosted CI
   job remains unverified until a remote is configured and the workflow runs.
7. Repeat the completed synthetic restore exercise with the operator's recovery
   procedure and separately preserved key, and verify private storage/Windows
   ACLs. Restore only trusted bundles: checksums are not signatures, and
   PostgreSQL dumps can contain executable database statements.
8. Verify operational limits with representative load. The bounded live store is
   estimated rather than a hard process-memory cap. Define log/audit/usage
   retention, alert handling and backup scheduling for the deployed machine.

The security review does not change services, rotate secrets, scan production,
create external issues or publish findings.

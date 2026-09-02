# Security by Design

Status: proposal. This becomes `SECURITY.md` and a set of tests once building starts.

## 1. Threat model summary

Assets: user accounts, the LLM and feed API keys held by the admin, saved reports and evidence, the host machine, and the outbound reputation of the app (it polls other people's servers).

Actors: anonymous internet users if the app is ever exposed; authenticated users acting beyond their role; hostile content authors (anyone who can publish a headline, a social post, or an RSS item that the app ingests); compromised or malicious upstream feeds; a malicious or misconfigured LLM endpoint.

Top risks, in order: prompt injection through ingested content; server-side request forgery through feed URLs or archive requests; credential theft; cross-site scripting through feed HTML or LLM Markdown; denial of service through oversized or slow upstream responses; authorisation bypass between users; supply-chain compromise of dependencies.

## 2. Controls

### Identity and sessions
- argon2id password hashing; password policy by length and an offline breach-list check, not composition rules.
- Access token: short-lived JWT (15 minutes) held in memory by the SPA. Refresh token: opaque, rotated on every use, stored hashed, delivered as an `HttpOnly; Secure; SameSite=Strict` cookie scoped to `/api/auth`. Reuse of a rotated refresh token revokes the whole family.
- CSRF double-submit token on cookie-bearing endpoints.
- Rate limiting and exponential backoff on login, account request, and password reset; temporary lockout with audit entry.
- Account requests go to a queue; nothing is active until an admin approves. Password reset tokens are single use, 30 minutes, hashed at rest; the response is identical whether or not the email exists. If SMTP is not configured, the admin can issue a reset link from the admin page.
- Optional TOTP second factor (phase 6), enforced for admins if enabled.
- Every auth event is written to the append-only audit log.

### Authorisation
- Two roles, `user` and `admin`, checked in the application layer, not only at the route.
- Object-level checks: reports, AOIs, collection plans, saved views and alerts belong to a user; access requires ownership or an explicit share. Admin endpoints require the admin role and are namespaced under `/api/admin`.
- A `Policy` module centralises these rules so they are unit tested once and reused everywhere.

### Untrusted content
- Every upstream response has a size cap (5 MB default, per connector), a timeout, and a content-type check. XML is parsed with `defusedxml`; JSON depth and size are bounded.
- Text fields are stripped of HTML with `nh3` and truncated. The frontend renders text nodes only; the sole HTML rendering path is the sanitised report Markdown, passed through DOMPurify with a strict allow-list.
- Outbound requests only to hosts declared by the connector or present in the admin-managed source registry. DNS results are checked against private, loopback, link-local and metadata ranges before connecting, and again on redirects.
- Adding or editing a source URL is admin only, validated (scheme, host, no credentials in URL), and logged.

### LLM boundary
- Evidence is presented inside clearly delimited data blocks with an explicit statement that it is untrusted content and not instructions. A heuristic scanner flags instruction-like text in evidence (for example "ignore previous instructions", "system prompt") and marks the item; flagged items are excluded from generation by default.
- The LLM has no tools with side effects. It returns a JSON document validated against the template schema. Citations are checked against the evidence bundle; unknown citations are removed and the report is marked with a validation warning. URLs in output that are not in the evidence are removed.
- Yardstick and confidence linting is applied to every key judgement; a report that fails validation is stored as `needs_review`, never silently published.
- Reports carry a permanent banner: machine-generated assessment from graded open sources; review before use.
- Prompts, model, endpoint, token counts and validation results are stored with the report for auditability.

### Secrets
- No secrets in code or in the repository; `.env.example` documents every variable. `gitleaks` in CI and pre-commit.
- Keys entered through the Admin UI are encrypted with Fernet using `ASE_ENCRYPTION_KEY`; only the last four characters are ever displayed; the API has no read-back endpoint.
- LLM API keys never reach the browser; all LLM calls are server-side.
- Tile services that need a key (OS Maps) are proxied through the API with a short cache so the key stays server-side and quotas are enforced per user.

### Transport and browser hardening
- HTTPS everywhere through Caddy; HSTS when exposed beyond localhost.
- Strict Content Security Policy: `default-src 'self'`; scripts only from self with hashes; `connect-src` limited to self and the tile hosts; `frame-ancestors 'none'`; `object-src 'none'`.
- `X-Content-Type-Options`, `Referrer-Policy: no-referrer`, minimal `Permissions-Policy`, CORS same-origin only.
- No third-party analytics or fonts at runtime; fonts are self-hosted.

### Availability and abuse
- Per-user rate limits on report generation and on expensive on-demand upstream queries; a global concurrency cap on LLM calls.
- Live store budgets prevent memory exhaustion; circuit breakers stop a misbehaving feed from consuming the poll loop.
- Backups: nightly `pg_dump` to a mounted folder with retention; restore documented and tested.

### Supply chain and build
- Pinned, locked dependencies (`uv.lock`, `pnpm-lock.yaml`); Dependabot or Renovate; `pip-audit`, `npm audit`, `bandit`, `semgrep`, `trivy` on images in CI.
- Docker images run as non-root with a read-only filesystem and a `tmpfs` for scratch; no added capabilities.

### Privacy and logging
- Structured logs redact tokens, keys and passwords; IP addresses are kept only in the audit log with a retention setting.
- The app stores no personal data beyond email, display name and audit events. Social-media items are held only in the expiring live tier unless a user pins them into evidence, which the audit log records.

## 3. Verification plan
- Unit tests for the SSRF guard, sanitiser, policy module, token rotation and validation linting, with coverage above 95 percent in those modules.
- A weekly dependency audit workflow.
- Before any exposure beyond the LAN: a self-review against the OWASP ASVS level 2 checklist, and an OWASP ZAP baseline scan against a staging container.

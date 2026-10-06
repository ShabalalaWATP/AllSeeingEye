# Security

The All Seeing Eye is a private, self-hosted hobby application. It is built on the assumption that every byte from the internet, every feed item and every LLM response is untrusted. The full design is in `docs/07_SECURITY_BY_DESIGN.md`; this page summarises what is implemented and how to report a problem.

## Implemented in Phase 0

- Passwords hashed with argon2id; a 12 to 128 character policy backed by a 10,000-entry common-password deny list that also catches common words with digits bolted on.
- Short-lived JWT access tokens (15 minutes) held in memory by the SPA; opaque refresh tokens in an `HttpOnly`, `SameSite=Strict` cookie scoped to the auth routes, rotated on every use, with family revocation when a rotated token is replayed.
- CSRF double-submit protection on the cookie-bearing endpoints, checked in constant time.
- Per-IP and per-email rate limits on every unauthenticated endpoint. Invalid passwords and MFA codes never create a persistent account lock that another person can trigger.
- No account enumeration: login failures, duplicate account requests and password reset requests for unknown addresses all answer exactly like the success path.
- Account requests are inert until an administrator approves them; activation and reset links are single use, hashed at rest and time limited.
- Authorisation enforced in the application layer with object-level checks (for example an administrator cannot demote or deactivate their own account).
- Security headers on every API response, `Cache-Control: no-store` on auth and admin routes, interactive API docs only in development.
- An append-only audit log of authentication and administration events.
- Server root secrets come from the environment. Model and FIRMS credentials may be stored encrypted under `ASE_ENCRYPTION_KEY`; APIs never return existing keys. FIRMS environment credentials take precedence over database configuration. Structured logs redact credentials, and secret-bearing FIRMS transport diagnostics are suppressed at their boundary.
- Locked dependencies audited in CI (`pip-audit`, `pnpm audit`, `bandit`, `gitleaks`); the API and web containers run as non-root users with read-only root filesystems.

## Reporting a vulnerability

Email the maintainer at [alexorr@yahoo.co.uk](mailto:alexorr@yahoo.co.uk) to report
a vulnerability privately. This channel does not require repository or GitHub
access. Alternatively, use
[GitHub private vulnerability reporting](https://github.com/ShabalalaWATP/AllSeeingEye/security/advisories/new)
to send a report to the repository maintainer. Sign in to GitHub, then select
**Report a vulnerability** from the repository's Security page. Repository write
access is not required. GitHub issues are public and are not a private reporting
channel.

Include the affected version or commit, reproduction steps using synthetic data,
the impact and any suggested fix. Do not attach live credentials, personal data
or private research. Keep exploit details private while the report is assessed.

This is a personal project without a dedicated security team. Acknowledgement
and follow-up are best effort, normally within one week; this is not a service
level agreement. If there is no reply, follow up in the same private email thread
or GitHub report.

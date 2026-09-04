# Security

The All Seeing Eye is a private, self-hosted hobby application. It is built on the assumption that every byte from the internet, every feed item and every LLM response is untrusted. The full design is in `docs/07_SECURITY_BY_DESIGN.md`; this page summarises what is implemented and how to report a problem.

## Implemented in Phase 0

- Passwords hashed with argon2id; a 12 to 128 character policy backed by a 10,000-entry common-password deny list that also catches common words with digits bolted on.
- Short-lived JWT access tokens (15 minutes) held in memory by the SPA; opaque refresh tokens in an `HttpOnly`, `SameSite=Strict` cookie scoped to the auth routes, rotated on every use, with family revocation when a rotated token is replayed.
- CSRF double-submit protection on the cookie-bearing endpoints, checked in constant time.
- Per-IP and per-email rate limits on every unauthenticated endpoint, and account lockout after repeated failures.
- No account enumeration: login failures, duplicate account requests and password reset requests for unknown addresses all answer exactly like the success path.
- Account requests are inert until an administrator approves them; activation and reset links are single use, hashed at rest and time limited.
- Authorisation enforced in the application layer with object-level checks (for example an administrator cannot demote or deactivate their own account).
- Security headers on every API response, `Cache-Control: no-store` on auth and admin routes, interactive API docs only in development.
- An append-only audit log of authentication and administration events.
- Secrets only from the environment; structured logs redact anything that looks like a credential.
- Locked dependencies audited in CI (`pip-audit`, `pnpm audit`, `bandit`, `gitleaks`); containers run as a non-root user with a read-only filesystem.

## Reporting a vulnerability

This is a personal project without a security team. If you find a problem, open a private issue or contact the repository owner directly rather than posting details publicly. Please include steps to reproduce and the version or commit affected.

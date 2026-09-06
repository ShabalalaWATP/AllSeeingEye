# Authentication and administrator API

Status: current implementation, 6 September 2026. FastAPI schemas and the exported
OpenAPI document are authoritative for field details. This document explains the
security contract; [team management](TEAMS_API.md) and
[scoped operational work](SCOPED_WORK_API.md) have separate contracts.

## Common rules

- Base path `/api`. JSON bodies and responses. All timestamps are ISO 8601 UTC.
- Error envelope: `{"error": {"code": "<snake_case>", "message": "<human readable>", "fields": {"<field>": "<reason>"}}}`. `fields` is optional; request validation and password-policy failures can provide it.
- Protected routes take `Authorization: Bearer <access_token>`. Missing or invalid token: 401 `unauthenticated`. Wrong role: 403 `forbidden`.
- Access token: JWT, HS256, claims `sub` (user id), `role`, `typ: "access"`, `iat`, `exp` (15 minutes by default), `jti`, `sid` (refresh family id) and `sv` (non-negative account security version). Held in memory by the SPA, never in persistent browser storage. Each protected request requires the current active account, matching security version and live family; role claims do not replace the current database role.
- Refresh token: opaque 48-byte URL-safe random string delivered only as the cookie `ase_refresh` (`HttpOnly; SameSite=Strict; Path=/api/auth; Max-Age=14 days; Secure` when `ASE_COOKIE_SECURE=true`). Stored hashed (SHA-256) with a family id; rotated on every refresh; reuse of a rotated token revokes the whole family.
- CSRF: cookie `ase_csrf` (random, `SameSite=Strict; Path=/`, readable by script) is set with the refresh cookie. `POST /api/auth/refresh` and `POST /api/auth/logout` require header `X-CSRF-Token` equal to the cookie (constant-time compare). Failure: 403 `csrf_failed`.
- Request bodies above 64 KB are refused with 413 `payload_too_large` (configurable with `ASE_MAX_REQUEST_BYTES`; Caddy enforces the same cap at the edge).
- Rate limits: 429 `rate_limited` with a `Retry-After` header. Defaults: login 10 per minute per IP and 5 per minute per email; request-account and forgot-password 3 per hour per IP; set-password 10 per hour per IP; authenticated password changes 5 per minute per account and per IP.
- Lockout: after 5 failed logins for one account within 15 minutes, the account is locked for 15 minutes. The response is still 401 `invalid_credentials`; the audit log records the lockout.
- No account enumeration: all login failures use a generic 401 response. Account requests and forgot-password requests use the same 202 message for known and unknown/ineligible addresses; they do not report whether an account exists.
- Security headers on every API response: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`, and `Cache-Control: no-store` on authentication, administrator and private operational routes. Binary document downloads preserve `private, no-store`.

## Objects

```
User            {id: uuid, email, display_name, role: "user" | "manager" | "admin", is_active: bool, created_at, last_login_at: datetime | null}
AccountRequest  {id: uuid, email, display_name, reason: string | null, status: "pending" | "approved" | "rejected", created_at}
AuditEntry      {id: int, at, actor_user_id: uuid | null, action, subject: string | null, ip: string | null, details: object}
TokenResponse   {access_token, token_type: "bearer", expires_in: int seconds, user: User}
```

## Endpoints

| Method and path | Auth | Body | Success | Errors |
|---|---|---|---|---|
| `POST /api/auth/login` | none | `{email, password, totp_code?}` | 200 `TokenResponse`; sets `ase_refresh` and `ase_csrf` cookies | 401 `invalid_credentials` (unknown email, wrong password, inactive, locked, missing/invalid required TOTP); 429 |
| `POST /api/auth/refresh` | cookie + CSRF header | none | 200 `TokenResponse`; rotates cookies | 401 `invalid_refresh` (missing, expired, revoked or reused); 403 `csrf_failed` |
| `POST /api/auth/logout` | cookie + CSRF header | none | 204; revokes the token family and its access JWTs; clears cookies | 403 `csrf_failed`; with valid CSRF, a missing refresh cookie still returns 204 |
| `POST /api/auth/request-account` | none | `{email, display_name, reason?}` | 202 `{"message": "If the address is eligible, an administrator will review the request."}` | 422; 429 |
| `POST /api/auth/forgot-password` | none | `{email}` | 202 `{"message": "If the address is registered, a reset link has been issued."}` | 422; 429 |
| `POST /api/auth/set-password` | none | `{token, new_password}` | 204 (token purpose may be `activation` or `reset`; single use) | 400 `invalid_token`; 422 `weak_password` with `fields.new_password` reason; 429 |
| `GET /api/me` | bearer | | 200 `User` | 401 |
| `POST /api/me/password` | bearer | `{current_password, new_password, totp_code?}`; extra fields forbidden | 204; changes only the authenticated account's password, ends all its sessions and outstanding password links, clears cookies | 401 for an ended/inactive session; 422 `invalid_request` for incorrect current password or required authenticator proof; 422 `weak_password`; 429 |
| `GET /api/admin/account-requests?status=pending` | admin | | 200 `{"items": [AccountRequest]}` | 401, 403 |
| `POST /api/admin/account-requests/{id}/approve` | admin | `{role: "user" | "manager" | "admin"}` | 200 `{"user": User, "activation_link": string | null, "expires_at": datetime}`; the link is returned when no email transport is configured | 404 `not_found`; 409 `already_decided`; 409 `email_taken` when a user with that address already exists |
| `POST /api/admin/account-requests/{id}/reject` | admin | `{reason?}` | 204 | 404; 409 |
| `GET /api/admin/users` | admin | | 200 `{"items": [User]}` | 401, 403 |
| `PATCH /api/admin/users/{id}` | admin | `{role?, is_active?}` | 200 `User`. A role/status change increments the security version and ends the user's sessions; deactivation also voids outstanding activation/reset links | 404; 409 `self_modification`; 403 if the actor loses administrator authority while waiting |
| `POST /api/admin/users/{id}/reset-link` | admin | | 200 `{"reset_link": string, "expires_at": datetime}` | 404; 409 `user_inactive` for a deactivated account |
| `GET /api/admin/audit-log?limit=100&before=<id>` | admin | | 200 `{"items": [AuditEntry], "next_before": int | null}` | 401, 403 |
| `GET /api/health` | none | | 200 `{"status": "ok", "version": string}` | |
| `GET /api/ready` | none | | 200 `{"status": "ready"}` when the database answers | 503 `not_ready` |

Interactive docs (`/api/docs`, `/api/openapi.json`) are served only when `ASE_ENV=dev`; the schema is also exported to a file by `uv run ase export-openapi <path>`.

Managers cannot call the administrator routes above. Assigning global `manager`
capability does not enrol the account into a team or grant access to another
team's work. There is no manager-accessible global user directory.

## Administrator TOTP

All these routes require the current administrator account and a bearer token.
TOTP is optional and uses six-digit authenticator codes. Existing active TOTP
secrets are never returned; only newly started enrolment discloses its secret.

| Method and path | Body | Result |
|---|---|---|
| `GET /api/auth/totp` | None | `{enabled, available}`; availability requires encryption configuration |
| `POST /api/auth/totp/enrol` | `{password}` | `{secret, provisioning_uri, expires_in: 600}` with `Cache-Control: no-store` |
| `POST /api/auth/totp/confirm` | `{code}` | 204; enables the pending factor and ends existing sessions |
| `POST /api/auth/totp/disable` | `{password, code}` | 204; removes the factor and ends existing sessions |

Accepted time steps are consumed atomically to prevent code reuse. Password
reset and role demotion do not delete a stored factor. A stored factor remains
required on login and authenticated password changes, including after demotion.
Host recovery uses
`uv run ase recover-admin-totp --email <account>` and requires password
confirmation; there is no HTTP recovery bypass.

## Account settings and password changes

User, manager and administrator accounts can change their own password through
`POST /api/me/password`. The endpoint has no target account identifier or role
field. It requires an explicit bearer token; refresh/CSRF cookies alone cannot
authorise the write. Both password fields accept at most 128 characters. A
supplied `totp_code` must be six ASCII digits and is required whenever the account
has an enrolled factor. A valid code already used at login cannot be reused.

The service locks the account and rechecks its active status and security
version before verifying the current password. The new password uses the policy
below. Wrong password or authenticator proof returns a generic 422 without
ending the existing session; it does not trigger the client's 401 refresh flow.
Locked accounts cannot use this endpoint until the lock expires or a valid
password reset completes.

A successful change commits the new hash, security-version increment, factor
code consumption, session/link revocation and audit entry together. Every old
access token, refresh family and unused activation/reset link for that account
is invalidated. The second factor and account role remain unchanged. The 204
response clears the current browser's cookies, and the client clears its access
token and returns to sign-in. Failed transactions do not consume a factor code.

## Session lifecycle and upgrade

Migration `0012` adds account security versions and the administration guard.
Old access JWTs lacking `sid`/`sv` are rejected. Existing valid opaque refresh
cookies can rotate into a new access JWT; revoked or expired sessions cannot.
The operator must migrate the intended database before starting the new code.
Development verification did not migrate the operator's database or `.env`.

Logout ends the presented family. Password changes, TOTP changes, account
role/status changes and recovery transitions invalidate affected account
sessions. Rotation uses atomic single-use claims and durable family revocation
markers. A successful refresh preserves its family and issues a new current
security-version JWT.

Administrator account mutations serialise through a shared guard, lock the
accounts in stable order and recheck the acting administrator. Self-modification
is refused. This preserves an active administrator across concurrent supported
role/deactivation requests without trusting an earlier request-layer check.

An open `/api/stream` rechecks identity and team authority before delivery and
every 15 seconds while idle. It sends `bye` with `session_revoked` when the
session ends, or `token_expired` at expiry. Membership/archive changes produce
`access.changed` so clients can discard stale scoped state.

## Password policy

12 to 128 characters; not in the bundled list of the 10,000 most common passwords, checked against the whole password and against its core with leading and trailing digits and punctuation stripped (so "password1234" is rejected); not equal to the email address or its local part. Violations return 422 `weak_password` with a specific reason in `fields.new_password`.

## Token links

Activation tokens last 7 days, reset tokens 30 minutes. Both are 48-byte URL-safe random strings (the same generator as refresh tokens) stored as SHA-256 hashes with a purpose and a single-use flag. Only an activation token turns an account on; a reset token for a deactivated account is refused with 400 `invalid_token`. Links are built from `ASE_PUBLIC_BASE_URL` as `<base>/activate?token=...` and `<base>/reset-password?token=...`.

Successful link redemption or an authenticated password change invalidates all
other outstanding password links for that account. Concurrent credential
changes serialise on the same account lock and cannot both overwrite a password
using stale proof.

## Audit actions

Authentication actions include `login_succeeded`, `login_failed`, `account_locked`,
`token_refreshed`, `refresh_reuse_detected`, `logout`, `account_requested`,
`account_request_approved`, `account_request_rejected`, `password_reset_requested`,
`password_set`, `password_changed`, `password_change_failed`, `user_updated` and
`reset_link_issued`. Password-change audit entries contain account identity,
action and request IP, never passwords, authenticator codes or session identifiers. TOTP actions additionally
record enrolment start, enablement, disablement, recovery and failures. The
current `AuditAction` enum is authoritative; team and operational actions share
the administrator-only audit log.

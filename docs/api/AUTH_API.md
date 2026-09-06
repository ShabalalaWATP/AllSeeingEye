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
| `POST /api/auth/login` | none | `{email, password}` | 200 `TokenResponse` and session cookies, or restricted `MfaPendingOut` without a session | 401 `invalid_credentials` (unknown email, wrong password, inactive, locked, invalid credentials); 429 |
| `POST /api/auth/refresh` | cookie + CSRF header | none | 200 `TokenResponse`; rotates cookies | 401 `invalid_refresh` (missing, expired, revoked or reused); 403 `csrf_failed` |
| `POST /api/auth/logout` | cookie + CSRF header | none | 204; revokes the token family and its access JWTs; clears cookies | 403 `csrf_failed`; with valid CSRF, a missing refresh cookie still returns 204 |
| `POST /api/auth/request-account` | none | `{email, display_name, reason?}` | 202 `{"message": "If the address is eligible, an administrator will review the request."}` | 422; 429 |
| `POST /api/auth/forgot-password` | none | `{email}` | 202 `{"message": "If the address is registered, a reset link has been issued."}` | 422; 429 |
| `POST /api/auth/set-password` | none | `{token, new_password}` | 204 (token purpose may be `activation` or `reset`; single use) | 400 `invalid_token`; 422 `weak_password` with `fields.new_password` reason; 429 |
| `GET /api/me` | bearer | | 200 `User` | 401 |
| `POST /api/me/password` | bearer | `{current_password, new_password, totp_code?, mfa_challenge_token?, mfa_code?}`; extra fields forbidden | 204; changes only the authenticated account's password, ends all its sessions and outstanding password links, clears cookies | 401 for an ended/inactive session; 422 `invalid_request` for incorrect current password or required authenticator proof; 422 `weak_password`; 429 |
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

## Multi-factor authentication

All active accounts can enable an authenticator app, email codes, or both from
**My account > Multi-factor authentication** (`/account/security`). Administrators
must keep at least one method enabled. After a valid password, accounts with MFA
receive a restricted challenge instead of access or refresh tokens. Administrators
without a factor must complete enrolment through that challenge before signing in.

`MfaPendingOut` contains `mfa_required: true`, opaque `challenge_token`, `expires_at`,
`methods` (`authenticator` and/or `email`), `enrollment_required` and `email_sent`.
An email-only login automatically sends a code. With both factors, the user can
choose email instead of the authenticator. Challenges expire after ten minutes;
email codes expire after five minutes and replacement codes invalidate prior ones.
Five failed attempts exhaust a challenge and count towards account lockout.

| Method and path | Auth / body | Result |
|---|---|---|
| `POST /api/auth/mfa/verify` | Challenge, `{challenge_token, method, code}` | TokenResponse and session cookies only after successful factor verification |
| `POST /api/auth/mfa/email` | Challenge, `{challenge_token}` | Sends or replaces login email code; MfaPendingOut |
| `POST /api/auth/mfa/enrol-app` | Restricted administrator enrolment challenge | `{secret, provisioning_uri, expires_in}`; confirm through `/verify` |
| `GET /api/auth/mfa` | Bearer | `{methods, available_methods, required}` |
| `GET /api/auth/totp` | Bearer | `{enabled, available}` |
| `POST /api/auth/totp/enrol` | Bearer, `{password}` | New secret/provisioning URI; expires in 600 seconds |
| `POST /api/auth/totp/confirm` | Bearer, `{code}` | 204; enables app and ends all sessions |
| `POST /api/auth/totp/disable` | Bearer, `{password, code}` | 204; removes app unless it is the administrator's final factor |
| `POST /api/auth/mfa/email/enrol` | Bearer, `{password}` | Sends purpose-bound enrolment code; MfaPendingOut |
| `POST /api/auth/mfa/email/enrol/confirm` | Bearer, `{challenge_token, code}` | 204; enables email and ends all sessions |
| `POST /api/auth/mfa/email/disable` | Bearer, `{password}` | Sends removal code unless administrator's final factor |
| `POST /api/auth/mfa/email/disable/confirm` | Bearer, `{challenge_token, code}` | 204; removes email and ends all sessions |
| `POST /api/auth/mfa/password-change` | Bearer, `{password}` | Sends purpose-bound email proof for `/api/me/password` |

Challenges are hashed at rest, purpose-bound, single-use and checked against current
account activity, lockout and security version. Email delivery releases database
locks and rechecks authority before accepting the delivery result. Authenticator
steps are consumed atomically. Existing secrets are never returned. Factor changes
revoke sessions and increment the account security version. Password resets and
role demotion retain enrolled factors.

See [MFA operations](../MFA_OPERATIONS.md) for encrypted authenticator storage,
SMTP configuration, migration and host-only recovery. There is no HTTP recovery bypass.
Incorrect personal verification passwords/codes return 422 without refreshing or
ending the caller's valid session. Invalid sessions still return 401. Public MFA
login failures remain generic 401 responses.

## Account settings and password changes

User, manager and administrator accounts can change their own password through
`POST /api/me/password`. The endpoint has no target account identifier or role
field. It requires an explicit bearer token; refresh/CSRF cookies alone cannot
authorise the write. Both password fields accept at most 128 characters. A
supplied `totp_code` must be six ASCII digits and is required whenever the account
uses its enrolled authenticator. Email verification instead requires a matching
`mfa_challenge_token` and `mfa_code` issued for password change. A code already used
at login cannot be reused.

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

Migration `0019` adds MFA challenges, email factors and refresh-family assurance.
Existing administrator sessions become unverified and must sign in again. Existing
authenticator secrets and replay counters remain intact. An unverified administrator
family cannot access protected routes, streams or refresh. Successful refresh preserves
MFA assurance. Migration `0012` introduced account security versions and the administration guard.
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


## Personal profile, sessions and recovery codes

All routes below require a live authenticated session and act only on the current
account, including when the caller is an administrator. Profile writes and session
mutations revalidate the original family under account locks. Browser mutations
abort on identity changes or unmount, preventing delayed 401 retries as a new user.

| Route | Behaviour |
| --- | --- |
| `GET /api/me/profile` | Returns name and saved preferences, or defaults |
| `PATCH /api/me/profile` | Partial update; unknown fields rejected, email/role/provider fields absent |
| `GET /api/me/sessions` | Up to 100 live families, current first, with truncation flag |
| `DELETE /api/me/sessions/{family_id}` | Revokes one owned family; current family clears cookies |
| `POST /api/me/sessions/revoke-others` | Revokes all other owned live families, including beyond list limit |
| `GET /api/auth/mfa/recovery` | Returns remaining count and availability, never code values |
| `POST /api/auth/mfa/recovery/challenge` | Fresh password starts purpose-bound email verification |
| `POST /api/auth/mfa/recovery/generate` | Fresh password and enabled factor proof replace the set and return ten codes once |

Profile fields are `display_name`, `timezone`, `date_format`, `research_mode`,
`research_languages`, `research_window_days`, nullable `research_country`,
`report_language`, `report_style` and `export_format`. The generated OpenAPI schema
is authoritative for enum values and bounds. Preferences cannot weaken evidence
policy or change administrator model configuration.

Recovery generation accepts `password`, `method` (authenticator/email), a six-digit
`code` and the email `challenge_token` where applicable. Incorrect proof returns
422 without ending a valid session. Codes contain 128 random bits each, persist as
hashes and are consumed once. The existing password-first login challenge advertises
`recovery` only when usable codes exist; `/api/auth/mfa/verify` accepts the code in
unseparated hexadecimal or hyphenated form. Recovery cannot enrol MFA or replace
the administrator's required factor. Migration `0020` adds preferences and `0021`
adds recovery hashes. See [profile operations](../PROFILE_OPERATIONS.md).

# Auth and Admin API Contract (Phase 0)

Status: agreed contract for Phase 0. The backend implements it; the frontend develops against it with MSW mocks and then against generated types from the live OpenAPI schema.

## Common rules

- Base path `/api`. JSON bodies and responses. All timestamps are ISO 8601 UTC.
- Error envelope for every 4xx and 5xx: `{"error": {"code": "<snake_case>", "message": "<human readable>", "fields": {"<field>": "<reason>"}}}` where `fields` is present only on validation errors (`code: "validation_error"`, status 422).
- Protected routes take `Authorization: Bearer <access_token>`. Missing or invalid token: 401 `unauthenticated`. Wrong role: 403 `forbidden`.
- Access token: JWT, HS256, claims `sub` (user id), `role`, `typ: "access"`, `iat`, `exp` (15 minutes by default), `jti`. Held in memory by the SPA, never in storage.
- Refresh token: opaque 48-byte URL-safe random string delivered only as the cookie `ase_refresh` (`HttpOnly; SameSite=Strict; Path=/api/auth; Max-Age=14 days; Secure` when `ASE_COOKIE_SECURE=true`). Stored hashed (SHA-256) with a family id; rotated on every refresh; reuse of a rotated token revokes the whole family.
- CSRF: cookie `ase_csrf` (random, `SameSite=Strict; Path=/`, readable by script) is set with the refresh cookie. `POST /api/auth/refresh` and `POST /api/auth/logout` require header `X-CSRF-Token` equal to the cookie (constant-time compare). Failure: 403 `csrf_failed`.
- Rate limits: 429 `rate_limited` with a `Retry-After` header. Defaults: login 10 per minute per IP and 5 per minute per email; request-account and forgot-password 3 per hour per IP; set-password 10 per hour per IP.
- Lockout: after 5 failed logins for one account within 15 minutes, the account is locked for 15 minutes. The response is still 401 `invalid_credentials`; the audit log records the lockout.
- No account enumeration: login failures, account requests for existing emails and password reset requests for unknown emails all return the same status and message as the success path.
- Security headers on every API response: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`, and `Cache-Control: no-store` on auth, me and admin routes.

## Objects

```
User            {id: uuid, email, display_name, role: "user" | "admin", is_active: bool, created_at, last_login_at: datetime | null}
AccountRequest  {id: uuid, email, display_name, reason: string | null, status: "pending" | "approved" | "rejected", created_at}
AuditEntry      {id: int, at, actor_user_id: uuid | null, action, subject: string | null, ip: string | null, details: object}
TokenResponse   {access_token, token_type: "bearer", expires_in: int seconds, user: User}
```

## Endpoints

| Method and path | Auth | Body | Success | Errors |
|---|---|---|---|---|
| `POST /api/auth/login` | none | `{email, password}` | 200 `TokenResponse`; sets `ase_refresh` and `ase_csrf` cookies | 401 `invalid_credentials` (unknown email, wrong password, inactive, locked); 429 |
| `POST /api/auth/refresh` | cookie + CSRF header | none | 200 `TokenResponse`; rotates cookies | 401 `invalid_refresh` (missing, expired, revoked or reused); 403 `csrf_failed` |
| `POST /api/auth/logout` | cookie + CSRF header | none | 204; revokes the token family; clears cookies | 403 `csrf_failed` (a missing cookie still returns 204) |
| `POST /api/auth/request-account` | none | `{email, display_name, reason?}` | 202 `{"message": "If the address is eligible, an administrator will review the request."}` | 422; 429 |
| `POST /api/auth/forgot-password` | none | `{email}` | 202 `{"message": "If the address is registered, a reset link has been issued."}` | 422; 429 |
| `POST /api/auth/set-password` | none | `{token, new_password}` | 204 (token purpose may be `activation` or `reset`; single use) | 400 `invalid_token`; 422 `weak_password` with `fields.new_password` reason; 429 |
| `GET /api/me` | bearer | | 200 `User` | 401 |
| `GET /api/admin/account-requests?status=pending` | admin | | 200 `{"items": [AccountRequest]}` | 401, 403 |
| `POST /api/admin/account-requests/{id}/approve` | admin | `{role: "user" | "admin"}` | 200 `{"user": User, "activation_link": string | null, "expires_at": datetime}`; the link is returned when no email transport is configured | 404 `not_found`; 409 `already_decided` |
| `POST /api/admin/account-requests/{id}/reject` | admin | `{reason?}` | 204 | 404; 409 |
| `GET /api/admin/users` | admin | | 200 `{"items": [User]}` | 401, 403 |
| `PATCH /api/admin/users/{id}` | admin | `{role?, is_active?}` | 200 `User` | 404; 409 `self_modification` when changing your own role or active flag |
| `POST /api/admin/users/{id}/reset-link` | admin | | 200 `{"reset_link": string, "expires_at": datetime}` | 404 |
| `GET /api/admin/audit-log?limit=100&before=<id>` | admin | | 200 `{"items": [AuditEntry], "next_before": int | null}` | 401, 403 |
| `GET /api/health` | none | | 200 `{"status": "ok", "version": string}` | |
| `GET /api/ready` | none | | 200 `{"status": "ready"}` when the database answers | 503 `not_ready` |

Interactive docs (`/api/docs`, `/api/openapi.json`) are served only when `ASE_ENV=dev`; the schema is also exported to a file by `uv run ase export-openapi <path>`.

## Password policy

12 to 128 characters; not in the bundled list of the 10,000 most common passwords, checked against the whole password and against its core with leading and trailing digits and punctuation stripped (so "password1234" is rejected); not equal to the email address or its local part. Violations return 422 `weak_password` with a specific reason in `fields.new_password`.

## Token links

Activation tokens last 7 days, reset tokens 30 minutes. Both are 32-byte URL-safe random strings stored as SHA-256 hashes with a purpose and a single-use flag. Links are built from `ASE_PUBLIC_BASE_URL` as `<base>/activate?token=...` and `<base>/reset-password?token=...`.

## Audit actions

`login_succeeded`, `login_failed`, `account_locked`, `token_refreshed`, `refresh_reuse_detected`, `logout`, `account_requested`, `account_request_approved`, `account_request_rejected`, `password_reset_requested`, `password_set`, `user_updated`, `reset_link_issued`.

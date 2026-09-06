# Multi-factor authentication operations

All users can configure MFA under **Account > Security > Manage MFA methods**.
Administrators must enrol one method after password verification before gaining a
session. Email and authenticator methods can both be enabled. Setting up another
method first allows administrators to remove a method without losing MFA protection.

## Configuration and upgrade

Before starting this version against an existing database, back up the intended
database and apply migrations through `0021` using the documented migration workflow.
No operator database was migrated during development. Existing administrator
sessions require a new sign-in; existing authenticator secrets remain valid.
Downgrade refuses configured factors to avoid silently deleting MFA protection.

Authenticator enrolment requires the existing persistent `ASE_ENCRYPTION_KEY`.
Keep that key backed up separately from the database. Email enrolment requires SMTP:

- `ASE_SMTP_HOST` and `ASE_SMTP_FROM_EMAIL` enable delivery.
- `ASE_SMTP_PORT` defaults to 587 and `ASE_SMTP_SECURITY` to `starttls`.
- Use `tls` for implicit TLS with the appropriate mail-server port.
- Set `ASE_SMTP_USERNAME` and `ASE_SMTP_PASSWORD` together when authentication is required.
- `ASE_SMTP_TIMEOUT_SECONDS` defaults to 10 (allowed range 1 to 30).

TLS certificate verification is mandatory. SMTP credentials are sent only after an
encrypted connection is established. Store configuration outside git. The same
transport delivers activation and reset links. Unconfigured email is shown as
unavailable; MFA codes are never returned through an administrator fallback link.
At least one method must be configured before an unenrolled administrator can sign in.

## Sign-in and recovery

A correct password opens the MFA step only when the account has an enabled factor,
or when an administrator needs mandatory enrolment. Login challenges expire after
ten minutes. Email codes expire after five minutes; wait at least one minute before
requesting a replacement. Use the newest code. An authenticator code is single-use,
so wait for its next time step when signing in immediately after profile enrolment.

Factor changes sign the account out on every device. Password resets retain MFA.
If email delivery fails, use an already enabled authenticator, a previously saved
recovery code, or restore SMTP service. Recovery codes are generated under
**Account > Security** after fresh password and factor verification. The set is
shown once, stored only as hashes, and invalidated by password or factor changes.
See [personal profile operations](PROFILE_OPERATIONS.md) for sessions and recovery.
Authenticator enrolment now includes a QR code generated locally in the browser.
For an administrator who has lost all usable factors, an authorised host operator can run:

```powershell
cd backend
uv run ase recover-admin-mfa --email <administrator-email>
```

The command requires the account password and explicit confirmation. It removes both
factors, revokes sessions and increments the security version. The next sign-in still
requires fresh MFA enrolment. The legacy `recover-admin-totp` command removes only the
authenticator. Neither operation has an HTTP equivalent.

## Verification limits

Development uses synthetic accounts, mocked SMTP and disposable databases. No real
mail delivery, production migration or operator recovery was performed. Configure the
host's encryption key or SMTP service and verify delivery before rollout. Local tests
do not establish deployment readiness.

# Personal MFA implementation review

Reviewed 6 September 2026 against the local working tree. No active production scan,
real credentials, external mail delivery or operator database changes occurred.

## Boundaries checked

- Correct passwords gate factor discovery and short-lived challenge creation.
- Challenge tokens are random, hashed at rest, purpose-bound and single-use.
- Six-digit email codes use the existing password-hashing boundary, expire after
  five minutes and are replaced on resend. Attempts and lockout are bounded.
- User locks, challenge revision checks and authenticator replay counters protect
  factor changes and completion. SMTP delivery does not hold database locks and
  rechecks account authority afterwards.
- Administrators cannot receive an unverified session or remove their last factor.
  Refresh and request validation require persisted MFA assurance for admins.
- Factor changes/recovery revoke sessions and increment account security versions.
  Recovery is host-only, requires the active administrator's password, and forces
  enrolment again. Password resets preserve factors.
- SMTP uses verified TLS/STARTTLS and does not log codes or credentials.
- Personal proof mistakes preserve valid sessions; public login failures do not
  trigger the authenticated client's refresh behaviour. Abandoned browser MFA
  completions cannot replace a newer signed-in identity.

## Findings resolved

Production structured tracebacks included local variables after the redaction
processor had run. A synthetic code/password/challenge marker reproduced disclosure.
Exception rendering now explicitly disables locals; the regression passes.

Personal MFA errors returned 401, causing the client to retry after refreshing and
then sign out. Invalid personal proofs now return 422; tests assert one failed
attempt, no refresh and a retained session. Actual invalid sessions remain 401.

The new MFA hook accepted responses after its page unmounted. Verification now uses
an abort signal and rejects abandoned responses or replacements of an authenticated
identity. A delayed-response regression covers leaving the page and signing in as
another account.

## Remaining operational limits

Expired challenge rows are not pruned automatically, although verification rejects
them. Track routine cleanup in the implementation plan. Migration `0019` and a
configured encryption key or SMTP service are required before administrator sign-in.
SMTP tests use mocks; actual host delivery remains an operator rollout check.

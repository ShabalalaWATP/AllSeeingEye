# Dedicated administrator workspace: scoped access review

Date: 6 September 2026.

This is a focused manual access review with synthetic regressions. It is not a
full-repository security scan or a production-readiness assessment.

## API access

A synthetic in-memory ASGI matrix exercised 23 administrator and administrator
TOTP operations against five caller states, for 115 checks. Anonymous callers
received 401; ordinary users and managers received 403. Administrators demoted
through the supported API received 401 using their old token. A directly changed
current role without a security-version increment still received 403. Private
responses carried no-store headers. No operator credentials or database were used.

## Fixed response boundary

A paused synthetic email sender reproduced a medium-severity disclosure: an
account approval could commit, the acting administrator could then be demoted,
and completion of email delivery still returned an activation link to that
revoked caller. A controlled post-commit reset-result hand-off covered the same
secret-response boundary without claiming reset issuance itself sends email.

Approval and reset-link routes now check the original token's session and current
administrator role using fresh committed state before constructing their response.
Eight regressions failed before the fix and passed afterwards, covering ordinary
demotion, role changes without a version increment, logout and token expiry.
They assert no returned link, no-store headers and exactly one retained authorised
account/token/audit transaction. No database lock is held across email delivery.

An independent 48-test backend selection passed, including the eight regressions
and existing account, user/audit, TOTP and model-connection lifecycle tests. Frontend
route guards protect the whole administrator shell, including `/admin/teams`;
the shared teams API retains its existing scoped manager/user permissions.

## Client visibility

The dedicated shell is verified on entry, focus and every 30 seconds while the
page is visible. Verification uses the captured bearer token with no automatic
refresh. A changed session hides the outlet until separately verified; a stale
response cannot overwrite a newer account or clear its session. In-flight
background checks preserve drafts, but a failed check or 15-second timeout hides
protected content and provides retry and return-to-research controls. Idle token
expiry requires sign-in again. This does not claim instantaneous pushed revocation.

Fourteen focused verification tests passed with 100% scoped gate coverage. The
fresh final frontend suite passed all 498 tests across 95 files, measuring 98.45%
line and 91.77% branch coverage. An earlier full run caught one legacy research
branding test using an admin route; it now tests the research route and the full
fresh run passed. Type checks, lint, formatting and production build passed, with
the existing map/deck bundle-size warning. Real browser checks at 1440, 390 and
320 pixels showed no overflow or page errors and verified keyboard focus and
demotion removing the protected page and administrator navigation. API responses
in browser checks were synthetic.

Seven existing report-session tests also passed after the shared response-check
helper change. Backend Ruff, formatting, strict mypy (376 source modules), Bandit,
architecture import contracts and file-length checks passed. OpenAPI export is
unchanged. This task did not remeasure whole-backend coverage or run its entire
suite; backend evidence is the scoped 48-plus-seven test selections above.

## Limits

Previously downloaded or seen information cannot be recalled. API checks remain
authoritative; hiding navigation is not an access-control mechanism by itself.
The checks here use scripted services and do not establish a production email
integration, a new deployment, or exhaustive race-freedom.

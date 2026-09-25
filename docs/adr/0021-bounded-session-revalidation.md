# ADR 0021: Release fence and bounded session re-validation

Status: accepted

Date: 25 September 2026

## Context

Every protected request validates the session at the start: the user is active, the
security version matches and the refresh family is live. Routes that release private
material after reads or slow work validated it again before returning. That second
check was written by hand in about 200 places across 36 routers, which mixed a
security policy into HTTP mapping and made a forgotten check silent.

Each re-validation also cost two database queries. HTTP requests often paid them twice
within milliseconds. Open streams re-read the session and full access context before
every message for every tab, although most messages carry shared public events.

## Decision

Routes take a request-scoped `SessionFence` (`api/session_fence.py`). `confirm()`
re-validates, `assert_live()` rejects an expired token with no await before release,
and `release()` does both for a finished value. Use cases receive the check through
one `SessionCheck` port. An architecture test fails when an authenticated route
neither takes the fence nor appears in a reviewed allowlist of routes that rely on
the start-of-request check alone.

A `SessionFreshness` cache lets `confirm()` and stream deliveries reuse a successful
database check of the same user, refresh family and security version when both hold:

- the check began less than `ASE_SESSION_RECHECK_SECONDS` ago (default 15, maximum 60);
- no committed change to that user's sessions or access has been signalled since it began.

Persistence adapters mark the affected users when they revoke refresh families,
change a user's security version, role or activation, or change team membership or
team state. The marks are published only after the transaction commits, and a
rollback discards them. Publishing wakes open streams through the event bus.

The start-of-request check still reads the database on every protected request.
Stream alerts, which are scoped private data, still re-read access before each
delivery.

## Consequences

- Short requests no longer repeat the session read before release. Streams read it at
  most once per window, or at once after a signalled change, instead of per message.
- Logout, revocation, password, MFA, role, activation and team changes made through
  the application end reuse immediately because they are signalled after commit.
- A change made outside this process, such as a CLI command or a direct database
  edit, can take up to the recheck window to affect a release fence or a stream's
  public deliveries. The start-of-request check sees it on the next request.
- Signals are in-process, which is valid because exactly one API process runs. More
  than one process would need a shared signal channel or the window as the only bound.
- Setting `ASE_SESSION_RECHECK_SECONDS=1` restores near per-release database checks.

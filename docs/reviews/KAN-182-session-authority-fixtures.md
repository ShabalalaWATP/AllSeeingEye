# KAN-182 session authority fixture repair

[CI job 114083207299](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38008101286/job/114083207299)
reported two failures after the idle-session changes. Both reproduced locally
against `054a1612`: two failed in 3.87 seconds.

- The report release-fence test supplied an `object()` refresh repository. The
  fence now reads family activity, so the fake raised `AttributeError` before
  reaching the intended check of token expiry after the fresh session closes.
- The token rollback test created a refresh token without persistent family
  activity. Atomic consumption correctly refused it before reaching the rollback
  assertions. Real login creates that activity through `SessionFactory.start`.

The repair updates only these fixtures. The fence fake supplies a typed activity
response with an idle deadline later than the token expiry, verifies the awaited
activity arguments, and requires the original token-expiry error after close.
The rollback fixture first checks that a missing activity record fails closed,
then creates the same family's activity. It retains every existing rollback,
exact-expiry, unknown-token and single-use assertion. Production code and
security checks are unchanged.

Validation: both complete files passed, 11 tests in 10.25 seconds. The group
includes blocked report creation/regeneration, independent-session token races
and the repaired boundaries. Ruff, formatting and `git diff --check` passed.
The coordinator independently reviewed the test-only diff without findings.
The touched test files are 116 and 184 lines.

Tests cleared shared database environment variables and used isolated SQLite.
No external providers, production services or shared databases were accessed.
Coverage, PostgreSQL and the full backend suite were not rerun for this repair.

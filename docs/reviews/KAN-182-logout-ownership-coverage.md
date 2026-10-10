# KAN-182 logout ownership coverage

The frontend aggregate for PRs 184, 189 and 190 failed the unchanged 95 percent
security branch floor for `src/stores/auth.ts`. The
[PR 190 CI job](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38008488527/job/114085693751)
and its coverage artefact recorded 66 of 70 branches, displayed by the gate as
94.29 percent. Lines and statements were fully covered. The new idle-session
code increased the module's branch denominator, exposing a gap in the existing
logout ownership tests.

`auth.logoutOwnership.test.ts` adds two behaviour regressions around a browser
session whose family identity has not yet been bootstrapped into memory. A held
Web Lock makes the ordering deterministic:

- An unchanged CSRF cookie permits exactly one logout after the lock releases.
  The test checks the real outgoing request's CSRF header and the absence of
  family and bearer headers.
- A cookie replaced by another tab while logout waits prevents any logout
  request. The replacement cookie and stored push ownership record survive,
  while the local session remains anonymous and its pending logout clears.

The tests use the real store and API client with MSW. No production code,
coverage exclusions or thresholds change. The original cookie-ownership check
is security relevant because a cookie-only logout must not revoke whichever
session another tab established while this tab waited for the shared lock.

Validation: all nine auth-store test files passed, 77 tests in 20.04 seconds,
with one worker. Focused `auth.ts` coverage passed the explicit 95 percent branch
gate at 68 of 70 branches (97.14 percent), with 100 percent lines and statements
and 96.15 percent functions. The two additional covered branches are the
cookie-only fallback decision and its changed-cookie refusal. A separate
reviewer checked the request barriers and ownership assertions without blocking
findings. This exercises stored push ownership, not a native service-worker
subscription. The full frontend suite was not rerun locally.

Targeted ESLint and Prettier, the complete frontend application TypeScript check,
and `git diff --check` passed. The new test file is 83 lines. All test requests
were intercepted locally by MSW; no real auth service or provider was accessed.

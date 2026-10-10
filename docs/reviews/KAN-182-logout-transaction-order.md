# KAN-182: session deadlines and revocation transaction ordering

The reported PostgreSQL logout timeouts came from test barriers that required an
impossible transaction order. Reviewing that boundary also exposed two real
session defects: expiry during an awaited authority read and refresh replay
revocation outside the account lock. Both now have production corrections and
deterministic regressions. Existing account locks and transaction ownership remain.

## Security corrections

`validate_current_session` previously captured time before awaited reads. A
confirmation could cross its access or idle deadline while the family read was
pending, then commit before its later disclosure check rejected it. It now reads
the activity deadline on successful validation too and checks both deadlines
synchronously after the final await. It remains read-only, returns the same user,
preserves `SessionIdleExpired` fields and never touches activity or commits.
Successful validation incurs one additional activity read.

An already-rotated refresh token previously reached reuse revocation before
acquiring the account lock. It could invalidate a family while a credential
transaction held that lock, after its authority query had read an active family.
Native PostgreSQL regressions demonstrated both persisted activation and metadata
release after completed revocation. The reuse branch now takes the same existing
account lock as normal refresh, logout and heartbeat. The durable family tombstone
remains, including its protection against descendants outside an update snapshot.
Replay may wait for an already-authorised guarded transaction to finish.

## Cause and boundary

FIRMS admission acquires the administration lock and the actor's account lock.
It retains those locks while reading or preparing credentials, rechecks authority
before committing, then acquires a new guard before releasing metadata. Logout
also acquires the account lock, shared with heartbeat, refresh and security changes.

The previous tests paused FIRMS inside its repository read or before its commit,
then awaited logout before allowing FIRMS to continue. Logout could not acquire
the account lock until the paused transaction finished. The production logout
paths do not contain that reciprocal wait: logout never requests the administration lock.

On the original candidate, both native PostgreSQL late-preparation cases timed
out at their existing ten-second bounds. Database observation identified the
logout `UPDATE users` waiting for the credential transaction. The revised native
test asserts that exact blocker relationship with `pg_blocking_pids` rather than
depending on a sleep or an assumed task schedule.

## Regression coverage

- A real logout completes before credential admission. Both status and activation
  fail with `Unauthenticated`; the stored credential revision remains unchanged
  and no confirmation audit is written.
- Logout starts while the credential transaction owns the account lock. It waits
  until that transaction commits, then completes before the separate disclosure
  check. Both operations refuse metadata and the activation resume callback is
  not called. A confirmation committed before logout remains committed. Refusing
  disclosure does not undo an earlier authorised transaction.
- Access expiry and idle expiry occur after status or confirmation preparation,
  before the mutation commits. Both deny release. A prepared confirmation and
  its audit are rolled back, preserving the previous revision, draft and test
  timestamp. Time can expire while the account lock is held, so this is a valid
  way to exercise the pre-commit rollback boundary.

The original ten-second native bounds and the suite timeout are unchanged. The
tests retain real repositories, use cases, independent PostgreSQL connections
and cancellation cleanup. Nearby revision, test-generation, administration and
publication races remain in the same native suite.

## Validation

The baseline was `d38bf7db`. The unrelated, reviewed fail-closed activity coverage
repair `2d57173b` was integrated before combined validation. A dedicated disposable
PostgreSQL container used the CI image:
`postgis/postgis:16-3.5-alpine@sha256:47e961a569fd52ff31f0fe205ed91eeab17d9f5fff6722e6d7ea6b588748b293`.
It had an isolated loopback port and generated local credentials. Shared database
and race URL environment variables were cleared before each run. No operator
database or external provider was used.

- Original native logout regression: **2 failed**, as expected, in 33.40 seconds.
- Revised admission and expiry cases on isolated PostgreSQL: **6 passed** in
  32.97 seconds.
- Entire native FIRMS concurrency file: **10 passed** in 60.90 seconds.
- Full source mypy: **passed**, 1,606 source files.
- Clock/read baseline: **8 failed, 1 passed**, including persisted confirmation
  after both access and idle expiry; the live read-only control passed.
- Corrected clock/read, MFA and activity boundary group: **35 passed** in 8.16 seconds.
- Native refresh-replay baseline: **2 failed** in 11.78 seconds, demonstrating
  persisted confirmation and released metadata after completed revocation.
- Final native FIRMS/replay group: **12 passed** in 64.93 seconds.
- Native refresh redemption, family revocation and idle races: **11 passed** in
  57.84 seconds, including the committed descendant and durable family marker.
- Final PostgreSQL pre-commit deadline cases: **2 passed** in 16.39 seconds.
- Final heartbeat own-read deadline fixture on PostgreSQL: **1 passed** in
  5.33 seconds after the fixture boundary correction.
- Final combined auth/FIRMS coverage group: **138 passed, 1 native-only skip** in
  83.36 seconds. `activity`, `current_session`, `refresh` and `sessions` each
  reached **100% lines and branches**, meeting their existing 95% floors. The
  skipped native refresh/replay case passed in the separate PostgreSQL group.
- Import Linter: **3 contracts kept**. Targeted Bandit, Ruff, formatting and
  `git diff --check`: **passed**.

The PostgreSQL commands, from `backend`, were:

```text
uv run --frozen --offline pytest tests/test_firms_credentials.py -k "completed_logout or expiry_during_preparation" --isolated-postgres --no-cov --tb=short -q
uv run --frozen --offline pytest tests/test_firms_credentials_concurrency_postgres.py --no-cov --tb=short -q
```

The first combined PostgreSQL invocation was rejected by the existing harness:
`--isolated-postgres` permits only `ASE_TEST_DATABASE_URL`, while the native FIRMS
fixture uses its own database URL. The runs were separated to preserve that
isolation check.

The first final auth coverage run passed all 138 tests (one native-only skip) but
showed that the stronger validator now intercepted the existing heartbeat
disappearance/deadline fixtures before the heartbeat's own defensive checks.
Those fixtures now let the real validator finish before removing the record or
crossing the deadline. They preserve the no-touch/no-commit/audit/token assertions
and the durable idle-revocation check, rather than assuming a fixed read count.

An initial independent review identified the clock/read and replay gaps. A fresh
independent review then examined both production corrections, all affected
callers, repository semantics and final regressions without actionable findings.
The reviewers did not execute tests. Every touched handwritten file is below
350 lines.

Coverage thresholds, API contracts and migrations are unchanged. Full repository
CI remains the integration gate.

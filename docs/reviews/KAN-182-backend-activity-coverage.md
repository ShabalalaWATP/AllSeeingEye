# KAN-182 backend activity boundary coverage

At commit `d346d2c8`, the
[backend aggregate CI job](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38010059593/job/114090567365)
passed the overall 90 percent coverage gate at 94 percent, then failed three
unchanged 95 percent security branch floors:

| Module | CI branch coverage | Missing behaviour |
| --- | --- | --- |
| `application/auth/activity.py` | 80.00% | Activity disappears after successful or idle-expired validation. |
| `application/auth/refresh.py` | 94.44% | Refresh rejects missing activity; logout revokes without an activity record. |
| `application/auth/sessions.py` | 75.00% | Session creation rejects missing or expired inherited family activity. |

The aggregate report identifies `activity.py:52->57,61`,
`refresh.py:67,152->154` and `sessions.py:58`. These are defensive branches in
existing production code, with missing regression coverage. No production
change, coverage exclusion or lower threshold is needed.

`test_session_activity_fail_closed.py` adds seven cases using normal persisted
login fixtures and real use cases. Heartbeat tests control the activity read at
the repository boundary to reproduce disappearance after validation. They
require the correct rejection, no heartbeat update, no commit and unchanged
audit/token/revocation state. Refresh and logout tests remove only the synthetic
family activity row in the private database. Refresh must not consume its token,
issue access credentials, recreate activity or commit; both explicit and
conditional logout must still persist family revocation and a logout audit.
Session factory tests reject both missing activity and the exact idle deadline,
without adding a child token or issuing access credentials.

The first local test-only run passed five cases and exposed a wrong literal in
the two new logout audit assertions. Both now use the existing domain enum.
This was a test-authoring correction, not a production regression.

The complete focused group passed: 92 tests across 11 files, with one
PostgreSQL-only test skipped, in 58.10 seconds. It includes the new boundaries,
idle behaviour and races, refresh/logout, durable revocation, token redemption,
account transitions, MFA assurance, access revocation and login. The three
affected modules each reached 100 percent lines and branches: activity 10/10,
refresh 36/36 and session creation 4/4 branches. The explicit 95 percent focused
coverage gate passed; coverage JSON also confirms every branch in each module.

Ruff, formatting and `git diff --check` passed. The new test file is 149 lines.
Tests used the private worktree environment and SQLite with shared database
environment variables cleared. No provider, production system or shared
database was accessed. The full backend/security-policy aggregate and native
PostgreSQL execution remain CI responsibilities for this test-only repair.

Independent source/security review found no actionable issue. It confirmed the
real validation and persistence paths, denied side effects, fresh-transaction
logout checks and exact-deadline session creation refusal. The reviewer did not
rerun tests; the measured results above are the implementation owner's evidence.

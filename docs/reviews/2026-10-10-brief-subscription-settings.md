# Brief subscription settings, KAN-229

The dedicated settings action and editor change only a subscription's name and
recurrence. They preserve the pinned Research Brief revision, owner/team,
collection policy, activation state and edition history. The ordinary full
subscription update remains unavailable for brief-linked subscriptions.

The configuration revision token excludes pause and execution activity. The SQL
update compares the expected editable configuration and pinned identity, then
patches only the permitted fields. Concurrent editors cannot silently overwrite
one another, and newer run bookkeeping remains intact. A name-only edit preserves
the due slot. Recurrence changes select the next matching future local slot.

## Validation completed

- A regression against immutable base `b1ea1a26` confirms that the new settings
  action was unavailable before this change.
- 56 focused backend tests passed across settings edits, independent SQL writers,
  brief creation, activation, session fences and calendar recurrence.
- The expanded coverage group covers 37 cases, including retained editions,
  expired sessions, foreign owners, ordinary team members, team managers,
  archived teams, disallowed payload fields, stale edits and nullable historical
  options. The PostgreSQL compilation assertion was updated for the null-handling
  wrapper and passed separately. There are 64 unique backend cases across these
  overlapping groups.
- Changed backend modules have 99.28% combined coverage: 122 of 122 statements
  and 15 of 16 branches. The sole uncovered branch is the optional absent session
  callback. Repository greenlet/thread instrumentation and the 90% gate are kept.
- Mypy, import boundaries, scoped Bandit, Ruff and changed-file formatting pass.
- Frontend type checking, lint and production build pass. Initial JavaScript is
  203,948 gzip bytes against a 245,760 budget; the globe route is 808,149 against
  870,400.
- Independent review covered the request surface, access/session checks,
  conditional SQL, revision identity and UI integration. A nullable-options issue
  was reproduced with both SQL and JSON null, fixed, and independently rechecked.
- All changed handwritten source files remain below 350 lines.

The coordinator's focused frontend run passed all 34 tests across six files:
`BriefScheduleEdit`, `briefScheduleEditing`, `BriefScheduleCopy.coverage`,
`schedules.controls`, `schedules.fieldErrors` and `BriefSubscriptionForm`.
These cover bounded requests, pending/error/success states, retained drafts,
stale revisions, cancellation, focus, unmount cancellation and structural
accessibility. Whole-branch CI and combined integration checks remain pending.

No PostgreSQL server was used: its statement was compiled, while execution and
concurrency checks used synthetic in-memory or disposable SQLite databases.
No production data, external provider or live deployment was touched. No migration
is required. See [subscription operations](../SUBSCRIPTIONS_OPERATIONS.md) for the
user and API behaviour.

## CI controls regression follow-up

PR #182 head `ef669a39` failed frontend shard 4 in
[job 114079552560](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/38006567692/job/114079552560).
The saved blob artifact, ID `11652635247`, contains one failed test and no
unhandled errors across 220 files. The older `briefScheduleControls` test still
required the pinned subscription's Edit button to be disabled, contradicting
KAN-229's supported name and recurrence editing. The KAN-206 remount changes do
not affect this assertion or its production path.

The corrected regression expects editable settings and checks the explanation
of their limited scope. Its MSW list response now reflects the paused state,
so the test waits for Resume, verifies Paused, and rechecks the unchanged pinned
Brief revision link after the refresh. Existing editing tests continue to verify
the exact bounded request and retained paused state. No production behaviour,
timeouts or coverage thresholds changed. The coordinator independently reviewed
this test-only correction without findings; the touched test remains 46 lines.

The corrected controls test and the two existing editing files passed together:
three files, 11 tests in 16.86 seconds, with one worker. Strict ESLint, Prettier,
application TypeScript and `git diff --check` passed. Coverage and the full suite
were not rerun for this test-only repair; combined CI remains the final gate.

# Report inventory monitoring

Status, 8 September 2026: integrated from feature commit `3ef66e9`, based on
integrated main `0c91741`. The merged backend/frontend runtime tree is identical
to the accepted feature tree; integration changes only these status documents.
Selected annotation monitoring and exact registry routing are merged. Combined
baseline validation passed on unchanged main `0c91741`: 3,278 backend tests passed,
55 skipped, with 95.06% coverage; 1,009 frontend tests passed with 90.11% branch
coverage, and the production build passed. This does not cover the inventory
changes in this branch. Its separate full run subsequently passed 3,291 tests,
with 70 skips and 95.05% coverage in 5,563.32 seconds.

## Operator outcome

An operator can monitor either selected annotations or the complete annotation
inventory of one saved report version. Inventory mode includes annotations added
after the monitor was created, including a report with no annotations initially.
The mode is explicit and immutable. Neither mode follows new report versions,
changes frozen evidence, nor recalculates the report's confidence assessment.

## Required behaviour

- Preserve existing monitors as `selected_roots`, with unchanged subscriptions,
  history, notification policy and alert acknowledgements.
- Admit `report_inventory` under the existing administration guard and current
  report/scope authorisation. Apply scope filtering before counts and limits.
- Capture every authorised root's current revision in a silent baseline. Zero
  roots is valid. More than twenty is an explicit capacity failure, with selected
  annotations offered as an alternative rather than a truncated inventory.
- Allow all three annotation categories in inventory notification preferences,
  even when a category is absent from the initial baseline. Preferences control
  alerts, not inventory membership.
- Persist creation events in the annotation creation transaction. A creation has
  no predecessor and refers to revision one, rather than whichever revision is
  latest when the observer runs.
- Fan out creations and appends to inventory subscribers by exact parent version
  and scope. This must handle creation followed by several appends before the
  first worker observation, and paused monitors. Deduplicate subscribers.
- Consume events in order. Adding a watch, advancing the checkpoint, storing the
  immutable comparison, creating an optional alert and consuming an event are
  one atomic operation with the existing checkpoint concurrency control.
- Treat a new root as an addition. Withdrawn roots remain part of inventory.
- Verify completeness against actual authorised roots and pending creation
  events. A missing unqueued root is a history gap, never an unchanged result.
- Creating a twenty-first annotation must succeed. Its monitor becomes explicitly
  unavailable for capacity, preserving its last valid checkpoint and history.
  Do not create a partial all-inventory manifest or misleading alert.
- Bound pending inventory events at 2,000 per monitor, independently of the
  2,000 retained-transition limit. Use a durable overflow/gap marker. Do not
  rely on the selected-root revision limit to bound an unlimited stream of roots.
  Preserve prior pending history and stop further accumulation after overflow.
- Preserve existing scope/global retention budgets, current-access checks,
  historical integrity checks, deletion semantics and notification privacy.
- Never silently rebaseline to recover from missing history or overflow.

## Migration and interface

The next migration must preserve existing checkpoints, watches, pending events,
transition digests and acknowledged alerts. Default existing rows to selected
mode. Refuse downgrade when inventory state or creation events cannot be
represented safely by the earlier schema.

Creation presents a clear mode choice and explains that a whole-report monitor
follows annotations on this saved version. Empty reports can start inventory
monitoring. List/detail views identify the mode and explain capacity failures.
Existing pause, catch-up, explicit fresh baseline and exact history remain
available within their validated limits. API types are generated after the
backend contract is stable.

## Acceptance checklist

Checked items reflect the focused local/PostgreSQL tests and source review.
Full backend regression acceptance and integration remain unchecked below.

- [x] Empty baseline, then creation and append, without report regeneration.
- [x] All three kinds, including a category absent from the baseline.
- [x] Creation and multiple appends before observation, including while paused.
- [x] Selected mode never automatically subscribes to new roots.
- [x] Multiple subscribers, competing workers, admission races and rollback.
- [x] Twenty to twenty-one roots: annotation creation succeeds, checkpoint is
  preserved, capacity is explicit, queue remains bounded.
- [x] Missing event, damaged anchor, wrong scope, revoked access and deletion.
- [x] Exact retained addition comparison survives later corrections and export.
- [x] SQLite and PostgreSQL migration preservation and unsafe downgrade refusal.
- [x] Frontend empty/error/capacity, mode, history and notification-scope cases.
- [x] Capacity-unavailable monitors still expose authorised retained history and
  explicit recovery actions. Access/integrity failures must not reveal stale
  private contents. The server validates each historical read and recovery.
- [x] Generated API, static checks and source/security review.
- [x] Full backend coverage against the integrated parent.
- [x] Merge into main and verify the accepted runtime tree is unchanged.

## Verification

Final local acceptance is 87 unique passing backend cases and 24 PostgreSQL
cases. Historical fixture Unicode was restored exactly and the six affected
SQLite migration cases passed again. Backend Ruff/format, mypy (614 source
files), both import contracts and configured Bandit passed. Independent source
review found no remaining issues. All repository hooks passed; Ruff/format and
Gitleaks were also run after staging the new files. The full isolated backend
run passed 3,291 tests, with 70 skips and 95.05% coverage. Its 1,018-test frontend
run passed with 90.18% branch coverage. The source remained frozen throughout
both accepted snapshots; only documentation was updated afterwards. These results
supersede pending local-check notes in the chronological record below.

The first backend snapshot passed eleven runtime cases (six new inventory and
five existing monitoring cases). Eight independent PostgreSQL concurrency cases
passed in 44.91 seconds. Eleven PostgreSQL migration cases passed in 47.11
seconds (five new 0031 cases and six historical 0030 regressions), covering
retained history, acknowledged alerts, schema parity and unsafe downgrade refusal.
All disposable PostgreSQL databases, container and volume were verified removed.
Five additional historical PostgreSQL migration cases passed in 13.26 seconds
after their setup was changed to explicit old-schema annotation writers. Original
schema, preservation and refusal assertions remain; disposable resources were
verified removed. The later local group passed thirteen runtime cases in 55.08
seconds. Final mypy passed 614 source files. The expanded group passed 36 cases;
one new HTTP test omitted its bearer header, reached authentication instead of
mode validation, and is being verified with the corrected fixture. Independent
backend source review reported no concrete production
findings. The frontend passed thirty focused cases and its type check;
production build passed. Its full run finished with 1,010 passes and five failures
in four existing login/map test files, including three whole-test timeouts.
The repaired unavailable-history UI subsequently passed 43 cases in seven files,
including authorised history/export/recovery and denied history. The four files
that failed in the full run passed unchanged in that focused group (13.73 seconds
total). This supports a timing explanation but does not replace a clean full run.
Final frontend lint and build passed. The full rerun passed all 1,018 tests in
198 files: 95.08% statements, 90.18% branches, 93.52% functions and 96.43% lines,
with unchanged gates. Frontend source is frozen and independent repair review
reported no further findings. Explicit fixed capacity/history-gap messages are
implemented and source-reviewed. Final focused backend acceptance passed 87 unique
local cases, including recovery and historical-schema fixtures. PostgreSQL
acceptance totals 24 cases, with the disposable resources removed. Ruff,
formatting, mypy, import contracts, configured Bandit and all pre-commit hooks
passed. File-based Ruff, format and secret checks were repeated after new files
were staged. Generated API export succeeded. The full backend coverage run and
integration were pending at that point. The full backend result above supersedes
that pending test status; merge verification also passed with no runtime changes.

Cross-version correspondence, original-source preservation, further collection
and media capabilities, map expansion, independent model evaluation and live
operational gates remain in the wider expansion plan. This milestone does not
replace those requirements.

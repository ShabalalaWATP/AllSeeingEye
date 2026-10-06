# KAN-81 panel body construction, 6 October 2026

Catalogue and traffic panel definitions now supply optional body factories.
GlobeControls resolves only the selected body's current factory, avoiding JSX
construction for closed catalogue and traffic panels on each live update.
Metadata, counts, callbacks and hooks still refresh normally. The selected body
continues to resolve when collapsed or while the chooser is visible, preserving
its existing state and lifecycle. Direct ControlPanel rendering supports both
ordinary React children and factories.

There is no body cache, new global state, permission change or altered stream
protocol. The canonical benchmark, synthetic fixture, dependencies and bundle
limits remain unchanged. Existing unknown-panel, removal, focus, selection,
correction and expiry behaviour is preserved.

The original implementation failed two intended body-construction regressions.
The final eight-file patch passes 37 distinct tests across 12 files, including
nine new cases. Scoped ESLint and Prettier, both full TypeScript configurations,
production build and existing bundle budgets pass. Initial/globe gzip sizes are
202,546/806,879 bytes against limits of 245,760/870,400. Every touched source file
is below 350 lines. Independent quality and security reviews cleared the final
production changes and both narrow test repairs.

The first candidate passed 34 tests and failed two new expectations: the existing
News panel intentionally has two regions, and dashboard selection requires the
real view owner. Those assertions were corrected without changing production
files or weakening freshness/access checks. The first full app type check also
caught an existing corridor test passing the new function-or-node union straight
to Children.toArray. That test now resolves the factory before its unchanged
assertions. All original failures and final owned-process cleanup receipts are
retained in the private lazy-panel-bodies/evidence/v1 packet.

Root applied the exact reviewed patch to PR 130's clean 4e637dcf base and verified
all eight source hashes and four protected input hashes. Patch SHA-256:
024ca02212e695ded6854b3b4823916ddf153bf8435627be4646c06bb98e6e67.
Evidence result SHA-256:
a72ac55f22ecb24c32963bb206d55222a266547cde9e5b25daf8f6a829677334.

## Published-head CI and dependency repair

At 1ae96222, CI 37444912235 finished with 29 successful jobs and one security
failure. All 4,596 frontend tests passed, with one skip. Coverage was 96.28%
statements, 92.26% branches, 94.76% functions and 97.43% lines; auth, global and
per-file floors passed. All four PostgreSQL shards passed. Their elapsed job
timestamps total 41.63 runner-minutes, or 42.17 including aggregation. This is
not a causal speedup comparison or KAN-71's 30-minute acceptance.

The security job failed on inherited source-map-js 1.2.1, affected by
[GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q).
Gitleaks was skipped after that audit failure, not passed. A separately isolated,
pnpm-generated patch changes only its lockfile package/snapshot to 1.2.2, official
integrity and four compatible resolved edges. No dependency range, override or
audit gate changes. Two independent static reviews are clear. The private frozen
install, audit (zero reported vulnerabilities), malformed/valid source-map
controls, full lint, both TypeScript checks, normal build, formatting and unchanged
bundle budgets pass. The unchanged magicast embedded copy was identified as a
scope caveat; no application attack path or universal dependency safety is claimed.
Fresh published-head CI is required after this repair.

At 435cbdf6, CI 37482425912 passed all dependency and security checks, including
Gitleaks, plus the frontend's 4,596 tests and unchanged coverage percentages.
All four PostgreSQL shards passed, totalling 39.67 runner-minutes, or 40.18
including aggregation. The overall run failed on one inherited SQLite test:
`test_last_event_id_header_resumes_over_http` advanced its fake clock after a
fixed sleep and received 401 before stream admission. A deterministic stream
barrier now waits for the matching replayed ASGI response frame before advancing
the clock. Both immediate and delayed admission reproduced 401 on the old test;
the repair passes the 31-case combined stream suite, including both cases. Authentication,
Last-Event-ID, replay and token-expiry assertions are preserved. Bounded waits,
closer cancellation/join and zero-held-slot checks prevent a hanging test.
Ruff, formatting and independent correctness/security review pass. The exact
one-file repair is integrated locally; new published-head CI is still required.

The separately reviewed Linux reference workflow is integrated as 966de7cd.
It keeps the original fixture, command and latency targets, with the historical
baseline explicitly normalised to the candidate's security-fixed dependencies.
Its 21 offline cases, Ruff and formatting pass. Independent review caught and
verified a launch-cancellation repair before execution. No hosted observation
has run yet. See the [protocol](2026-10-06-KAN-81-linux-reference.md).

## Canonical v5 failed attempt

The unchanged new pair stopped on a baseline TimeoutError, before any completed
test or scenario metrics. The candidate was not run. All pre/post source, shared,
runtime/dependency and retained-evidence pins matched. Owned cleanup terminated
the job, found no remaining members, observed process exit and closed all handles
without errors. Raw failure evidence and exclusive observation remain retained;
there was no unchanged retry. The tool connection returned a requested 50-second
wait after 2,990.26 seconds. The 6,549.89-second receipt envelope cannot establish
test runtime or the cause of the delay. Neither interval is application latency.

The previous canonical v4 candidate still misses the original median/maximum
targets. KAN-81 remains open pending fresh CI, measured latency and real-browser
validation.

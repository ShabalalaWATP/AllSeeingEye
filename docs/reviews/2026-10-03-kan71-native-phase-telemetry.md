# KAN-71 native test phase evidence

The final PR #121 CI run, `37083781451` at `1a8a672b`, passed with
2,895 selected PostgreSQL-lane cases. Its four native jobs and coverage merger
used 2,751 seconds (45.85 runner-minutes), above the 30-minute acceptance target.
The retained slowest-20 summaries exposed only 160 phase records, including no
teardown durations. They do not establish a safe optimisation large enough to
close that gap. Earlier local comparisons remain separate evidence and are not
projections of hosted savings.

This change records complete emitted pytest phase reports on the existing
PostgreSQL lanes. It changes reporting only:

- Native commands use `--durations=0 --durations-min=0` instead of showing only
  the slowest 20 phases. SQLite commands retain their existing reporting.
- An explicit `--record-test-phases` option enables one controller writer. Each
  lane has a separate fresh `.controller.jsonl` file; xdist workers do not open
  it. Forwarded reports retain their actual worker identity when available.
- Records contain the original node ID, setup/call/teardown phase, raw pytest
  duration and outcome. They exclude exception text, captured output, fixture
  values, SQL, locals and user properties. Session records identify the schema
  version and final exit status/report count when pytest reaches session finish.
- Each complete line is flushed through line buffering. A partial failed or
  interrupted session remains readable. Existing files are refused rather than
  overwritten, and a separate `always()` artifact upload retains available
  reports even when the test step fails.

Node IDs retain pytest parameter IDs, as existing CI evidence does. This is an
allowlist of report fields, not a general secret-redaction mechanism; test IDs
must not contain private data.

This is per-case phase evidence, not per-fixture or template-admission profiling.
Setup and teardown include all work that pytest attributes to those phases.
Concurrent phase durations must not be added and described as elapsed job time.
An absent session footer or missing expected case/phase requires investigation;
the existence of an artifact is not proof that the full lane completed.

Selection, original test bodies, worker counts, native database ownership,
authentication, coverage collection and all aggregate gates are unchanged. No
fixture, admission, SQLAlchemy or application hooks are wrapped or replaced.
The recorder is registered explicitly beside the existing pytest plugins and
does nothing unless its option is supplied.

Validation includes real serial and two-worker pytest subprocess sessions with
passing cases, parameterisation, skipped cases, setup/call/teardown failures,
raw duration retention and unique phase records. Additional controls cover
disabled/worker registration, partial evidence, refusal to overwrite and the
runner's distinct native-lane output names. The child failures are intentional;
their parent regression tests must pass.

Local validation passed all seven recorder cases and 14 shard-runner cases,
scoped Ruff lint/format, Actionlint 1.7.7 and this note's formatting check.

Independent source quality and security reviews found no actionable issue.
The first hosted artifact still needs reconciliation against the actual selected
node IDs and test outcomes. Printing all phases and writing JSONL add reporting
overhead, which remains part of the measured hosted job cost.

KAN-71 remains open. A complete qualifying hosted run and the required five
before/five after comparison are still needed. This reporting milestone makes
no performance claim and does not manually dispatch or repeat workflow runs. Any subsequent
KAN-70 observation must review the exact reporting-only shard-runner delta as a
new immutable source variant before changing its accepted input map.

The publication tree normally integrates the separately reviewed KAN-81
frontend checkpoint and its locale-equal ID stable-order repair at `85edcce9`.
The combined tree passed 162 focused frontend cases in 22 files. Its frontend
bytes match that reviewed revision; backend reporting bytes match `4d5865d5`.
The dependency lock, canonical benchmark and fixture match released `8c0b93cf`.
The frontend's earlier timings are pre-repair observations, not timing evidence
for this final source. Its targets and real-browser trace remain outstanding,
as recorded in the [KAN-81 note](2026-10-03-KAN-81-live-event-latency.md).

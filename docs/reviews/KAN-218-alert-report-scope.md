# KAN-218: exact alert report scope

The initial regression showed that a two-country, five-minute rule produced an
unrestricted report request with a rounded one-hour interval. Delayed admission
could also observe live evidence that had changed since the alert fired.

## Scope and evidence

The alert transaction now retains a versioned, bounded snapshot of the rule origin
and its cited EvidenceItems. This is frozen report evidence, not a general event
archive. The snapshot has the existing 20-item citation bound and the report codec's
768 KiB limit. Oversized or unavailable evidence fails report admission visibly;
the alert itself still persists. Common alert reads defer loading the snapshot.

The origin records the alert and rule IDs, rule revision, owner/team, exact interval,
country set, rectangle, categories, keywords, severity floor, full observed match
count and cited IDs. The interval includes the firing instant at datetime precision
and honours a later rule resume boundary. Existing rectangle-over-country precedence
is retained. Report rules reject more than eight or invalid ISO countries; exact
shapes continue to be explicitly unsupported for automatic reports.

Durable jobs consume only the frozen cited sample. Live mutation, eviction, later
events, model-directed extra terms and optional reranking cannot add other events.
Instruction-like cited items are retained in the snapshot for provenance but excluded
from model evidence. The prompt and saved scope identify the sample; reports with
more matches than citations retain an explicit evidence-sample finding. The saved
report carries the original scope and source evidence for traceability.

Current owner/team authority and the original rule revision remain required at
admission, execution and publication. Manual regeneration is explicitly refused;
resume uses the original durable job. Normal report requests retain their old
idempotency hashes when the new internal origin is absent. No public request schema
accepts an alert origin, and no provider or external research is invoked in tests.

## Compatibility and rollout

Migration 0091 follows 0090 and adds one nullable JSON field. Old pending intents
without a snapshot become failed with `evidence_unavailable`. Old queued alert jobs
without an exact origin pause with `invalid_snapshot` and cannot resume. Historical
alerts and completed reports remain readable. Downgrade refuses to remove retained
frozen alert evidence. SQLite migration tests use a disposable database; PostgreSQL
and production rollout remain release gates.

Apply migrations before new workers. Drain or cancel pending admission before any
rollback to code that predates exact snapshots: retaining the schema is insufficient
when an older worker ignores the new snapshot. Normal report workflows are unchanged.
KAN-219 template validation and KAN-220 firing deduplication remain separate work.

## Verification

Focused regressions cover two-country five-minute scope, category/keyword/severity
exclusions, future evidence, antimeridian rectangles, bounded samples versus full
counts, live mutation/eviction, frozen publication, malformed snapshot identity,
legacy pending/queued jobs, manual regeneration refusal, normal request identities,
and migration upgrade/guarded downgrade. Existing queue, cancellation, recovery,
permission and report-job tests are included in the focused verification group.

The initial two-country regression failed before the fix. The final focused group
passed all 55 tests across 11 test files. Ruff check and formatting, mypy across
1,596 source files, three import-linter contracts, Bandit on changed Python, and
`git diff --check` passed. All changed handwritten Python files are below 350 lines.
Coverage was not measured, and the full suite was not run. No public API schema or
frontend changed, so generated types and frontend builds were not required.

The independent source and security review found no blocking issues. It checked
origin identity and scope consistency, country ordering, exact interval bounds,
frozen selection, exclusion of instruction-like evidence, prohibition of fresh
collection, access/revision fences and legacy migration behaviour.

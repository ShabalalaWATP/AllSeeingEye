# Cross-version monitoring

Status, 8 September 2026: proposed and unimplemented. This document records the
next complete delivery after pinned selected-root and report-inventory monitoring.
It does not claim implementation, test acceptance, model validation or deployment.
Existing source remains frozen while the inventory integration suite runs.

## Operator outcome and scope

An operator can opt into monitoring successive saved research results, inspect the
exact before/after evidence and assessments, and receive scoped change alerts.
A monitor has one immutable origin:

- `report`: successful regenerated versions of one explicit report ID.
- `research_schedule`: successful executions of one explicit schedule ID. Each
  current scheduled execution creates a different report root at version one.

These origins are not interchangeable. Manual regeneration of a report produced by
a schedule does not become a scheduled execution. Arbitrary report IDs or similar
questions do not establish membership of a research series. Changing origin or
scope requires a new monitor, not an implicit reassignment.

Pinned annotation monitors remain independent. Cross-version snapshots include
annotations present at successful publication; later annotation creation or review
is observed by the pinned monitor rather than silently changing an older
cross-version comparison.

## Existing behaviour and success semantics

The existing implementation provides several reusable boundaries:

- [ReportStatus](../backend/src/ase/domain/reports.py) has `READY`, `NEEDS_REVIEW`
  and `FAILED`. [compare_reports](../backend/src/ase/domain/research_changes.py)
  rejects `FAILED` as a new baseline and retains the preceding baseline ID. Both
  other statuses currently participate in deterministic report comparison.
- [SaveProduction.save](../backend/src/ase/application/reports/save_production.py)
  performs the final authorised transaction for the report, automatic claim
  revisions and audit. A publication must be recorded after these claims, before
  that transaction commits.
- [schedule_report](../backend/src/ase/container/features.py) creates a report for
  each scheduled execution and returns its report ID. It does not regenerate a
  standing report root.
- [SqlScheduleStore.mark_run](../backend/src/ase/adapters/persistence/schedules.py)
  authorises the current schedule and records its result in a later transaction.
  [record_change](../backend/src/ase/adapters/persistence/schedule_changes.py)
  compares exact version one with the preceding successful version and stores
  `last_change`; this is not a durable transition ledger.
- [annotation_deltas](../backend/src/ase/domain/annotation_deltas.py) supports
  same-root continuity and explicit one-to-one annotation correspondence.
  [confidence_deltas](../backend/src/ase/domain/confidence_comparison.py) supports
  declared judgement pairs and unique identical statements. Reused judgement IDs
  alone do not establish correspondence.

Proposed publication admission preserves the existing non-failed rule:
`READY` and `NEEDS_REVIEW` are persisted, comparable results; `FAILED` is not a
new successful baseline. Here, successful means production completed sufficiently
to retain a comparable report. It does not mean that the assessment is validated,
accurate, approved or ready for operational use. Preserve status and validation
findings prominently in each side, transition and alert detail. A `NEEDS_REVIEW`
result remains explicitly in need of review, including when it changes a baseline.
Cancelled, rolled-back and failed production cannot advance a monitor checkpoint.
A missing or incomplete frozen assessment cannot imply confidence direction.

## Durable publication and scheduled execution

Add an immutable successful-publication record containing a server-generated ID,
origin, origin sequence, exact report/version ID, report status, source scope,
content/evidence digests, publication time, and all current annotation revision
references. Bound the combined annotation inventory to twenty roots, including
zero and withdrawn roots. Scope filtering precedes count and cap-plus-one queries.
Capture exact revisions after automatic claim persistence under the same guard.
Do not resolve later heads when the background observer eventually runs.

For scheduled work, add a durable run identity before production, recording the
schedule ID, configuration revision, owner/scope and execution sequence. Pass this
identity through a server-only production context, never ordinary client report
input. The final production transaction rechecks current schedule/run authority
and writes the successful publication, exact result association and per-monitor
outbox deliveries together with the report. A later `mark_run` acknowledges this
same result idempotently; it must not create an independent second publication.

On restart, reconcile committed unacknowledged successes before deciding to run
the same scheduled occurrence again. Distinguish an acknowledged failure from a
committed success awaiting acknowledgement. A crash before commit leaves no
success; a crash after commit cannot lose it. A configuration change during
research must not attribute its result to the new configuration. Preserve the
existing final scope checks and define explicit stale-run handling.

For report-origin monitors, publish each qualifying saved version after final
production, once. Version-number gaps caused by failed attempts are legitimate.
Order by the successful-publication sequence, not a requirement that the next
version number equal the last number plus one.

Monitor admission and publication use the same administration guard. Creating a
monitor captures the latest authorised successful publication silently, or enters
`awaiting_first_success` if none exists. The first qualifying publication becomes
a silent baseline. Never guess historical schedule membership from matching
questions, report titles or timestamps. Existing schedules without a durable run
ledger need a documented, validated baseline reference or a fresh first success.

## Observation and immutable history

Process queued publications sequentially. Each accepted transition contains the
exact previous successful checkpoint and the next publication, frozen comparison
method/results/digest, configuration revision, notification policy, server actor
attribution and source run/publication identifiers.

The following belong to one guarded transaction:

1. Recheck active owner, current scope and background capability.
2. Validate both retained report versions and all exact annotation anchors.
3. Verify expected configuration, publication order and checkpoint identity.
4. Store immutable comparison and optional generic alert.
5. Advance the checkpoint and consume that subscriber's event using CAS.

Unavailable authority, missing parents, invalid digests, incomplete publication
history or capacity preserve the last valid checkpoint. Do not turn unavailable
input into a withdrawal, an unchanged result or a new baseline. A later successful
publication does not erase an earlier unprocessed success. Failed research does
not advance either the version monitor or the existing research baseline.

## Correspondence and interpretation revisions

Automatically compare evidence by exact `(source_id, event_id)` identity and use
the existing unique identical-statement rule for judgements. Same annotation roots
retain their existing continuity rule; different cross-version roots remain
unmatched additions/removals. An addition/removal is relative to these snapshots,
not evidence that an underlying entity appeared, disappeared or changed ownership.
Do not introduce fuzzy text, reused-ID or implicit source-name matching.

Operators may declare up to twenty one-to-one same-kind annotation pairs and
twenty judgement pairs between the exact retained transition sides. Each requires
a bounded rationale, current write authority and server-derived author attribution.
Keep declarations separate from source assertions and verified identity.

Record these declarations as an immutable, CAS-protected interpretation revision
of that transition, with its own comparison digest. Preserve the original automatic
comparison and every prior interpretation. This action does not advance the
research baseline, rewrite an earlier alert or silently carry a declaration to
unknown future roots. A later version requires its own valid correspondence.
The first delivery does not require automatic semantic annotation matching.

## Notification categories

Expose six implemented categories:

- `evidence`: exact inventory/content/source-flag changes.
- `claims`: substantive claim differences and unmatched annotation additions/removals.
- `identity`: captured identity-review differences and unmatched roots.
- `relationships`: captured relationship-review differences and unmatched roots.
- `judgement_links`: changed supporting/opposing evidence for established
  judgement correspondence, with unmatched assessments explicitly identified.
- `confidence`: recorded confidence/ceiling changes for comparable frozen
  assessments, or explicit availability/method limitations without an invented
  numeric direction.

Link changes alone must not trigger a confidence-change claim. Preserve existing
link-conditioned confidence-swap detection where correspondence is unchanged.
Suppress order-only/provenance-only differences, retaining them in exact history.
Do not describe an operator interpretation revision as new research. If separate
interpretation notifications are introduced, label their origin explicitly.

Alerts contain generic counts/category identifiers and an exact transition link,
not source excerpts, private question text or full frozen snapshots. Team alerts
are team-visible; they are not personal notifications. External delivery remains
an explicit separate capability. Existing schedule alerts remain compatible;
the UI must make overlapping opt-ins clear rather than silently changing them.

## Limits, pause and recovery

Initial proposed bounds are twenty annotation roots per side, twenty judgement
pairs and twenty annotation pairs per interpretation, one hundred pending
successful publications per monitor, and ten thousand pending deliveries globally.
Count pending reference payload bytes against the shared retention budget as well
as enforcing counts. Retain the existing twenty monitors per scope, one thousand
monitor records globally, sixty-four MiB per scope, two hundred and fifty-six MiB
globally, eight MiB per complete manifest and two thousand retained transitions
as combined limits across monitor types, not separate allowances that multiply
storage. Interpretation revisions also consume retained count and bytes.

A successful research save must not fail merely because a subscriber cannot
retain its next delivery. Persist a bounded overflow/gap marker, preserve existing
pending sequence and stop further accumulation for that subscriber. A publication
with more than twenty annotations cannot produce a truncated whole-inventory
comparison. Show the capacity failure and offer an explicitly narrower workflow.

Pause retains pending publications. Resume offers explicit catch-up or a fresh
baseline. Fresh baseline records which source sequence interval is skipped and
suppresses individual alerts for those skipped results; it does not erase history.
Policy changes require equivalent explicit checkpoint semantics. A missing parent
or still-oversized inventory cannot be recovered by pretending it was read.
Provide authorised CAS deletion to reclaim monitor data without deleting reports.

## Privacy, persistence and migrations

Use `AccessPolicy.background` for current active-owner/team checks, including
membership requirements for administrators. Store no refresh token or credential
for background work. Bind publications, runs and monitors to exact scope. Query
visibility before limits/counts; origin identifiers supplied by a client are not
authorisation. Archived/deleted origins and changed memberships stop observation.

History and export remain available for capacity-unavailable monitors where the
caller still has current authority and exact inputs remain intact. Recheck both
parents under one final shared guard. Keep asynchronous HTTP session checks before
the final guarded operation and synchronous expiry checks afterwards. Downloads
return the retained manifest, never a comparison recomputed against latest.

Add a real version-monitor alert origin with matching transition reference and
extend the exactly-one-origin constraint without fabricating a research schedule.
Preserve all previous alert acknowledgements. Report, schedule and monitor cleanup
must remove or invalidate associated deliveries/alerts consistently, including
SQLite without foreign-key enforcement. Do not leave readable private summaries
behind after their authorising parent disappears.

Migration must preserve existing annotation modes, checkpoints, transition hashes,
queued corrections, schedule `last_change`, reports and acknowledged alerts.
Refuse downgrade while new run/publication/monitor/interpretation state cannot be
represented safely, including damaged orphan rows. No operator database migration
is part of local acceptance.

## Concrete implementation boundaries

Proposed new modules, split by responsibility and kept within repository limits:

- Domain version-monitor, successful-publication and interpretation-revision types;
  a version-monitor change classifier reusing existing comparison functions.
- Application ports for successful publications/runs and version-monitor storage.
- Application report-publication admission, version-monitor management,
  observation, history/export and correspondence-interpretation services.
- Persistence models/repositories for durable runs, publications, per-subscriber
  outboxes, checkpoints, transitions and interpretation revisions.
- Thin version-monitor API schemas/routes and container factories/worker wiring.

Extend `save_production.py` after automatic claims, server-only generation context,
`schedules/runner.py`, schedule production wiring and `SqlScheduleStore.mark_run`
for durable run identity/reconciliation. Extend alert mapping/constraints and
parent cleanup. Reuse the existing comparison side resolvers, digest/render limits,
background runner recovery, current-access policy and final dual-parent recheck.
Do not make the container own polling or comparison policy.

Frontend delivery needs origin-aware creation, explicit success/status semantics,
pending/unavailable/recovery states, exact historical before/after evidence links,
six category controls, interpretation revision selection and one-to-one pairing
with rationale. Generate DTOs from the backend; do not infer matching in the UI.

## Acceptance checklist

- [ ] Report-origin and schedule-origin creation, including no prior success.
- [ ] READY and NEEDS_REVIEW statuses remain distinct and truthfully displayed.
- [ ] Success, failure, success compares the two successes without losing history.
- [ ] Scheduled crash before/after report commit and before/after acknowledgement;
      restart reconciliation produces one publication/transition/alert.
- [ ] Multiple successful results before observation preserve every intermediate
      change and reversal, including legitimate failed-version gaps.
- [ ] Automatic claim publication is atomic; later annotation edits do not alter
      the frozen cross-version snapshot.
- [ ] Exact evidence and judgement matching; reused J1, duplicate statements and
      different annotation roots remain unmatched without a valid declaration.
- [ ] Bounded one-to-one declarations, actor attribution, stale CAS, immutable
      interpretation history and no accidental research-baseline movement.
- [ ] All six categories, link-only versus confidence changes, confidence swaps,
      unavailable assessments and changed-method limitations.
- [ ] Empty/complete/over-cap annotations, pending/global/byte limits, overflow,
      pause, catch-up and explicit skipped-interval rebaseline.
- [ ] Current scope filtering, inactive/removed owners, archived origins,
      administrator membership, deletion and historical export/revocation races.
- [ ] Competing publishers/observers, duplicate acknowledgement, transaction
      rollback and restart through independent PostgreSQL connections/locks.
- [ ] SQLite/PostgreSQL migration preservation, exact old hashes/acknowledgements,
      clean empty roundtrip and refusal with retained or damaged new history.
- [ ] Production-path tests through SaveProduction and scheduled generation,
      plus frontend behaviour, generated schema, static/security checks and
      broader integration coverage with unchanged gates.

These checks define the smallest complete proposed delivery: both real successful
result streams, durable automatic observation, exact retained comparisons and
explicit interpretation, end-to-end alerts and recovery. Implementing only new
pinned-version annotation controls would not satisfy this plan. Wider collection,
original-source preservation, independent model evaluation and operational release
gates remain separately tracked.

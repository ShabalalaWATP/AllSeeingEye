# Reproducible annotation comparisons and meaningful-change monitoring

Implementation contract, 7 September 2026. Comparison preview/export and
confidence explanations are integrated on main in `d37f723`, with full backend
acceptance still in progress. Durable
monitoring checkpoints and their alerts remain planned work. It preserves the expansion requirements for changed
claims, identity and organisation assertions, evidence-linked confidence
explanations, and opt-in meaningful-change alerts.

## Existing behaviour and verified gap

`comparison.py` compares report versions but does not resolve independent
annotation revisions. `schedule_changes.py` compares newly collected version-one
reports. Annotation roots belong to an exact report version, so their IDs cannot
establish continuity across newly collected reports.

`research_changes._relationships()` counts judgement support/opposition links,
not organisation edges. Its confidence counter also includes those links. A
local synthetic probe reproduced a missing confidence reason when support links
and recorded confidence changed together from high to low: only
`evidence_relationships_changed` was returned. Replacing `elif` with `if` alone
would introduce false confidence notifications for link-only changes. Repair
must distinguish an actual recorded confidence difference from a changed link
key, and retain existing relabelling/order suppression.

## Immutable comparison inputs

Capture exact report/version IDs, evidence and report-content digests, timestamp
and bounded explicit root/revision references for claims, identity decisions and
relationship reviews. Resolve them through current-authority services, using
the exact-selection and final-recheck pattern already used for exports. Do not
resolve both sides as latest when rendering a historical comparison.

Same-root revisions can be compared directly. Different roots remain distinct
unless an explicit operator correspondence is supplied and preserved. Fuzzy
text, names, shared addresses or reused judgement labels do not establish
identity or claim continuity. Exact source/event record correspondence may be
shown separately without implying reviewed entity or relationship continuity.

Classify changes to statement, kind, disposition/review state, rationale,
conflicts and citations separately. Keep both immutable revision IDs, author
and time, and side-specific evidence links. Distinguish a withdrawal decision
from evidence missing in a later collection window.

## Preview and export contract for the first delivery

The first delivery uses stateless preview and export backed by exact persisted
report and annotation revisions. A new comparison table is not required for
this step. The downloaded manifest preserves the resolved inputs, method and
results; durable monitoring checkpoints remain a separate required delivery.

Each side accepts at most twenty selected annotation revisions, with at most
one revision of a given root per side. Explicit same-kind correspondence is
one-to-one, bounded and attributed as an operator declaration, not verified
identity or semantic equivalence. The manifest attributes the comparison and
its operator declarations to the authenticated requesting account, supplied by
the server and included in the digest. It does not replace the separate authors
of selected review revisions. Report sides must share the same personal
owner or team scope. Current read authority is required for both sides and
every selected revision, including historical reads.

Export supplies the preview digest. That digest covers resolved input content,
comparison method/version and result, rather than only client reference IDs.
The newly issued response timestamp is excluded from this stable digest. A
change in selected content or comparison policy/output between preview and
export must be rejected, with final authority and content rechecks after
rendering. The final validation holds the shared administration guard across
both parents and every selected revision until one final commit; nested
resolution must not commit or release that guard between sides. Independent
PostgreSQL contention tests must verify the boundary against normal guarded
application mutations. Generated-at records response time, not a trusted capture
time.

Keep complete source snapshots in the sides. Separate provenance-only changes
such as a version-local label or recapture timestamp from substantive assertion
changes, especially for explicitly paired cross-version identity/relationship
reviews. A real parent endpoint, source status or validity-period change must
remain visible. This distinction will support later notification suppression
without erasing the original records.

## Confidence explanations

Use frozen assessment inputs and outputs: supporting/opposing evidence,
reliability and information credibility as separate dimensions, contribution
tiers, copy/organisation groups, balance, ceiling, final confidence, method
version and existing explanations/limitations. Match evidence using both source
and event ID; labels alone are local to a report version.

Judgement correspondence needs an explicit or documented unambiguous exact rule.
Repeated J1 identifiers do not prove that two statements mean the same thing.
Where correspondence is unresolved, show separate assessments rather than an
invented directional confidence change. Explain observed changes without
claiming unique causation or a probability that a statement is true. Disclose
method-version differences rather than recomputing old reports under new rules.

## Monitoring checkpoints

Keep successful research baselines separate from annotation-observation
checkpoints. A checkpoint freezes exact watched revision references and its own
identity/digest. Observe changes before advancing it. An annotation correction
must remain detectable after report generation, and a failed research run must
not erase valid annotation changes or advance the successful research baseline.

Use the existing fresh-authority schedule guard, transactional alert insertion
and compare-and-swap pattern. Deduplicate the same checkpoint transition on
replay. Monitoring is opt-in, with separate evidence, claim, identity,
organisation relationship, judgement-link and confidence categories. Suppress
unchanged and administrative-only notifications without erasing their history.
Access loss is unavailable monitoring, never inferred withdrawal. Incomplete or
oversized inventories must not be presented as complete unchanged observations.
Private snapshots and excerpts must not enter shared SSE payloads.

## Interface, export and acceptance

Extend existing report comparison and schedule interfaces with separate change
sections, exact revision links and side-specific evidence navigation. Alerts
must link to the frozen transition, not whichever report happens to be newest.
Export a bounded manifest of the immutable inputs and deltas, rechecking every
parent scope and selected content after rendering.

Required behaviour tests include same-root corrections/withdrawal, distinct
cross-version roots, event-ID collisions across sources, citation relabelling,
simultaneous support/confidence changes, link-only changes, ambiguous judgement
correspondence, method changes, missing assessments, valid versus capture time,
checkpoint replay/CAS, corrections during failed research, incomplete inventory,
revocation/deletion, mixed annotation selections and export-time mutation.
Persisted checkpoints require SQLite/PostgreSQL preservation and contention
acceptance. These checks do not replace independent human semantic evaluation.

## Acceptance in progress

Four independent PostgreSQL tests passed in 13.86 seconds for the final release
boundary. Preview and export each verify that an authorised report-deletion
operation waits on an observed administration lock until both parent checks
finish. Deletion committed during rendering, before that guard, prevents
release. Distinct database backend IDs and observed lock waits establish real
contention. All disposable databases, the owned PostgreSQL 17.10 container and
volumes were verified removed. Log:
`data/annotation-comparison-concurrency-postgres.log`.

The isolated full frontend suite passed 978 tests in 185 files: 95.12%
statements, 90.17% branches, 93.61% functions and 96.42% lines. Two subsequent
small paging/type and lint repairs passed affected runtime tests, type checks
and production build. Final global lint passed. Backend focused acceptance
passed 120 cases, with one mixed-selection fixture missing its required company
subject scope. The fixture-only repair then passed that remaining case. All 121
selected cases therefore passed across the broad run and targeted repair. Whole
backend Ruff/format, mypy (595 source files), both import contracts and Bandit
passed. Final integrated backend coverage remains outstanding. The full-suite log is `data/annotation-comparison-full-coverage.log`.

Two pre-existing fixture repairs are isolated commits on the same branch:
closing the AidData catalogue SQLite inspection connection passed all four
catalogue tests with allocation tracing and ResourceWarning enabled, and adding
the relationship selection default to the export admission fake passed all ten
admission/revocation cases. Neither repair changes production behaviour or
weakens the assertions. Main's pre-comparison full backend run finished with 3,146 passes, 35 skips,
five failures from the old export admission fixture and one SQLite resource
warning (95.26% coverage). The isolated fixture repairs address these known
issues; integrated acceptance must still verify the combined tree.

Final read-only review found no additional actionable issues across comparison
validation, current access, digest binding, scoped search and frontend scope
invalidation. All repository hooks passed, including Gitleaks, Ruff/format,
file-length checks and full frontend lint/type checks. No live provider, browser
or human assessment acceptance is implied.


## Operator workflow

Open the report comparison view and choose the before and after report/version.
The searchable report chooser includes older reports through pagination. Select
exact historical claim, identity or organisation-review revisions on each side,
up to twenty combined and one revision per root. A comparison may use two
revisions within the same report version.

Same-root revisions correspond automatically. For different roots or judgements,
declare correspondence only when justified and record the rationale. The server
attributes the declaration to the requesting account. Inspect annotation changes,
side-specific evidence and frozen confidence explanations separately. Export JSON
from the preview to preserve its exact inputs, method, results and digest. If the
selected content changes before export, preview again. A preview does not create
a monitoring subscription.

## Integration record

Feature `090743f`, LF normalisation `737cdee` and fixture repairs `5776aaa` and
`dbf6db4` are merged into main at `d37f723`. Backend and frontend Git tree hashes
match the accepted comparison branch exactly. Full integrated backend acceptance
is running in `data/annotation-comparison-integrated-backend-full.log`. The 978
frontend tests and full lint/type/build results apply to that identical frontend
tree; no second identical full frontend run was required. There is no Git remote,
operator migration or production deployment.

## Phase 3 implementation decisions

Standalone monitors will observe selected annotation roots without requiring
report regeneration. Start with an explicitly disclosed selection of up to twenty
roots on one exact report version. This does not claim discovery of newly created
roots or complete report inventory monitoring.

Insert an ID-only outbox event inside each annotation mutation transaction. Record
the exact committed revision and predecessor so rapid reversals are observed in
order, including changes made before worker restart. Audit rows are not the queue.
Creation captures an authorised baseline without an alert. Configuration changes
use CAS and an explicit new baseline. Pause preserves history; resume distinguishes
catch-up from deliberately establishing a fresh baseline.

Under the shared administration guard, recheck background authority and scope,
resolve the exact event, then atomically persist the immutable transition,
checkpoint advancement, optional alert and event-delivery state. CAS and unique
transition identity prevent replay duplicates. Suppress provenance-only alerts
while preserving their history. Missing anchors, corrupt snapshots, overflow or
history gaps preserve the valid baseline and disclose unavailable monitoring.
Never translate loss of access into a withdrawal.

Extend the alert origin constraint to support a real annotation monitor and exact
transition ID alongside existing indicator and schedule origins. Preserve old
alerts and acknowledgements. History/detail/export must resolve the immutable
transition with current authority, not recompute against latest or redirect to a
newer report. Store bounded manifests and disclose retention/expiry. Private
snapshots and excerpts must remain outside shared SSE messages.

Research successful baselines remain separate. Annotation changes must survive
failed research runs. Cross-report correspondence remains explicit; standalone
same-version monitoring cannot imply fresh evidence or new model confidence.
SQLite/PostgreSQL migration preservation, competing-worker CAS, rapid reversal,
rollback/restart, unavailable recovery and export/revocation contention tests are
required before acceptance.


## Remaining monitoring scope after selected-root delivery

The first standalone monitor delivery does not complete all comparison monitoring
requirements. Keep these follow-on requirements open:

- Complete-inventory monitoring must observe newly created roots through a bounded
  authorised count plus cap-plus-one inventory, and report overflow/inconsistency
  explicitly. A selected-root subscription must never be labelled all annotations.
- Cross-version monitoring needs an explicit correspondence contract and frozen
  transition before/after references. Distinct annotation roots remain unmatched
  unless an operator declaration or documented exact rule establishes the relation.
- Future evidence, judgement links and confidence changes use new report versions
  and their separate successful-research baseline. Pinned-version controls must
  not expose selectable categories that cannot change. Existing research schedule
  alerts are useful but do not establish annotation-aware historical transitions.
- Multi-monitor delivery is keyed per monitor, configuration and event. One
  subscriber consuming an event must not hide it from another. Retention must
  preserve each paused/unavailable subscriber's required history or explicitly
  report a gap; it must not silently reset to latest.
- Report/monitor deletion must remove or invalidate alert summaries, transition
  references and outbox delivery state consistently, including SQLite operation
  where foreign-key enforcement is disabled. Existing alert reads cannot be
  assumed to validate a deleted annotation parent.

These are part of the full expansion goal. Separate bounded deliveries organise
implementation and verification; they do not redefine completion.

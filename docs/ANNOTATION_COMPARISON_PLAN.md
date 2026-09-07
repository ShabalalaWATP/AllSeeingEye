# Reproducible annotation comparisons and meaningful-change monitoring

Implementation contract, 7 September 2026. Comparison preview/export and
confidence explanations are implemented on the isolated
`codex/annotation-comparisons` branch, with acceptance still in progress. Durable
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

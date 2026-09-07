# Reproducible annotation comparisons and meaningful-change monitoring

Implementation contract, 7 September 2026. This is planned work following the
isolated relationship-review milestone, not a claim of implemented comparison
or monitoring features. It preserves the expansion requirements for changed
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

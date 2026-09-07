# Dated relationship assertion review

Implementation contract, 7 September 2026. The isolated
`codex/relationship-review` branch contains the implementation in progress;
acceptance and integration into main are not yet complete. It advances the E6/E7
requirement that assertions retain type, time validity, source references,
review state and disagreement. It does not replace the remaining source-depth,
identity, comparison, alert or human-evaluation requirements.

## Evidence boundary

The existing GLEIF adapter captures direct and ultimate accounting-consolidation
relationships. The report view preserves source status and original period
metadata. Neither an accounting-consolidation assertion nor a shared address
establishes beneficial ownership, a verified identity match or current validity.

Introduce a server-side projection of exact frozen source assertions before
accepting operator reviews. Initially support the GLEIF records already shown by
`organisationRelationships.ts`; unsupported sources/types remain explicitly
unreviewable through this contract. Additional relationship sources need their
own validated projection rather than a generic parser that guesses semantics.
This first source-specific delivery does not complete every organisation edge
required by the full plan.

Validate the source ID, record kind, original relationship type, child/parent
LEIs and duplicate/missing attributes. Retain original period types and strings,
including missing or truncated metadata. Distinguish relationship periods,
source-record validity, publication, capture and review timestamps. Do not
derive a current-validity flag from any one of these fields.

## Immutable review and disagreement

A relationship review is independent from identity-match decisions. Eligibility
depends on captured supported relationship evidence, not an explicit company
subject or an earlier identity decision.

Each root binds the report and exact version, whole-version evidence digest,
evidence label, event/source IDs, source-content hash, server-derived assertion
snapshot, owner/team scope and creator. A different assertion requires a
different root. Operators cannot replace the source endpoints, relationship
type, dates, report version or raw attributes through a review form.

Each append-only revision retains its predecessor, number, author/time,
`supported`, `disputed`, `unresolved` or `withdrawn` disposition, required bounded
rationale, unresolved-disagreement notes and exact supporting/opposing/context
excerpts. These are operator assessments, not source facts or changes to the
original evidence. Reject an initial withdrawn revision. Preserve attributed
contrary assessments in history when a later reviewer changes the disposition.

One shared root per exact assertion provides chronological disagreement and
correction history. It does not imply simultaneous independent reviewer votes
or a consensus score. Those would need an explicit separate contract.

## Authority, persistence and limits

Follow the existing identity-review transaction pattern: administration guard,
account lock, fresh current-session and object/action access checks, quota
admission and compare-and-swap on the latest revision. Do not hold database locks
across model or rendering work. Validate retained assertion and revision integrity
on reads, not just at creation.

Use the established scope limits of 1,000 roots and 64 MiB, at most 100 revisions
per root, 20 citations, 20 bounded disagreement notes and pages of 20. Charge
canonical bytes for every retained revision. Scope is the personal report owner
or team, not merely the latest reviewer. Keep identifier-only audit records.

Add a migration after the actual current head, with independent SQLite and
PostgreSQL schema/preservation checks. Refuse downgrade while review history
exists. Explicit report-deletion cleanup must also work when SQLite foreign-key
enforcement is disabled. Production/operator migration remains a separate action.

## Review, history and export experience

Keep the source-reported relationship visible alongside its dated evidence and
separate operator assessment. Provide an editor, attributed history, stale-edit
conflict recovery and exact evidence navigation. Clear private drafts when the
account, workspace, report or version changes. Do not merge identity and
relationship review controls or describe them as interchangeable.

Add explicit relationship revision references to the existing combined limit
of 20 selected annotations in an evidence package. Include the frozen assertion,
dates, assessment, rationale, disagreements, excerpts and revision provenance.
Resolve scope and immutable selection before rendering, then recheck current
authority and exact selected content afterwards. A newer revision must not
replace a selected historical one. Preserve the package byte/admission limits.

Organisation-edge and review-aware comparison/alerts remain required later work.
The existing `research_changes._relationships()` concerns judgement support and
opposition labels; do not silently reinterpret it as organisation-edge history.

## Required acceptance

- Source projection: direct/ultimate assertions, unsupported types, malformed
  LEIs, duplicate/missing attributes and missing/truncated periods, without
  invented ownership, identity or validity conclusions.
- Immutable anchors: snapshot/excerpt tampering, cross-version labels, changed
  parent scope and preserved source endpoints/dates across corrections.
- Lifecycle: initial withdrawal refusal, revision continuity/cap, stale-CAS
  conflict, deletion cleanup and exact historical selection.
- Authority: personal/team isolation, read-only member mutation denial, current
  session/MFA revocation and identifier-only audit output.
- Independent PostgreSQL transactions: competing quota admission, CAS and
  access revocation while a writer waits on an observed database lock.
- Migrations: SQLite/PostgreSQL parity, existing report preservation, clean
  downgrade/re-upgrade and downgrade refusal with retained history.
- Exports: relationship-only and combined packages, exact selection limit,
  cross-version refusal and revocation/mutation during rendering.
- UI: separate source/assessment semantics, history, conflict recovery,
  evidence navigation and private draft invalidation.

These engineering checks cannot supply independent human judgement about whether
a source assertion is accurate or whether an operator's assessment is sound.

## Operator workflow

Open the required saved report version, then expand **Relationship reviews and
history**. The captured-relationship picker shows supported source assertions.
Choosing an already-reviewed assertion opens that review, including when its
entry is on another results page. Incomplete or unsupported source records
remain available through the evidence annex.

Read the original child/parent identifiers, relationship type, source status
and dates before saving an assessment. Choose **Unresolved**, **Supported** or
**Disputed**, explain the assessment in the required rationale, and optionally
attach exact supporting, opposing or contextual excerpts. Record unresolved
conflicts separately. **Withdrawn** is available when correcting an existing
review, rather than creating one. The app preserves the earlier assessment and
does not overwrite the captured source record or its grades.

Use **Relationship revision history** to inspect earlier attributed revisions.
Corrections require current permission. Team members can read shared history;
correction follows the existing author, team-lead and administrator policy.
If another edit has already been saved, the stale correction is rejected. The
reload action explicitly discards the local draft and fetches the current
review; it does not silently merge two assessments.

Select the particular revision to include it in an evidence package. The
shared limit is twenty selected claims, identity reviews, relationship reviews
and original assets combined. A selected historical review remains that exact
revision even if a newer correction exists. Its predecessor identifier is
provenance, not a claim that every earlier revision is included in the package.
Access and selected content are checked again before download.

Dates are deliberately kept distinct. A source status of ACTIVE is a recorded
registry assertion. An accounting period, publication date, capture date or
review timestamp alone does not establish present validity or beneficial
ownership. This workflow records the operator's assessment and its evidence;
it does not calculate a consensus vote or a probability that the edge is true.

## Local acceptance, 7 September 2026

Seven independent PostgreSQL concurrency cases passed in 29.43 seconds on a
fresh PostgreSQL 17.10 instance. The tests cover competing personal/team root
and byte quota admission, stale service revisions, repository compare-and-swap
and membership revocation while a writer waits. Separate backend process IDs
and observed database lock waits establish real contention for quota, service
revision and revocation cases. The test databases, container and volumes were
removed after verified ownership and absence checks. No operator database or
credentials were used.

Four additional PostgreSQL migration cases passed in 12.56 seconds. They
verified migration 0028 to 0029 schema parity and constraints, preservation of
existing reports and account/provider data, clean downgrade/re-upgrade, and
no-write downgrade refusal when complete or damaged history remains. The
separate disposable databases, container and volumes were verified removed.
Logs are retained locally under `data/relationship-concurrency-postgres.log`
and `data/relationship-migration-postgres.log`; these are ignored test artefacts.

The backend type check passed across 580 source files. OpenAPI and frontend
types were regenerated from the isolated backend. Frontend acceptance passed
54 focused cases covering new review flows and existing identity/export/report
regressions, along with type checks, scoped lint and a production build. Final
relationship tests were rerun after the fixture/type adjustments. A review
identified and corrected duplicate-create navigation: the server now supplies
an authorised existing-review mapping independent of list pagination. The
regression for opening an existing review beyond the first page passed.

The clean combined backend run passed 133 tests in 203.73 seconds, including
new service, projection, export, SQLite migration and unchanged legacy
claim/identity export and repository tests. Earlier local acceptance had 63
passes and two test expectation failures; those expectations were repaired for
the independent relationship package manifest and duplicate-selection error.
Existing claim and identity package versions remain unchanged when relationship
revisions are absent. The clean log is `data/relationship-focused-recheck.log`.

Whole-backend Ruff, formatting (971 files), mypy (580 source files), both import
contracts and configured Bandit passed. Repository file-length and whitespace
checks passed. Read-only review covered immutable payload validation, source
projection, current-session/scope checks, export admission and final rechecks,
and downgrade/deletion behaviour; no unresolved actionable issue was found in
that scope. This is scoped engineering review, not a live security assessment.
All repository hooks passed, including secret detection and full frontend lint
and type checks. Combined integration and full-suite acceptance remain required.

The complete expansion goal, broader relationship source support, human
assessment quality and operator migration remain open. The implementation
remains on its isolated branch pending integration into main.

# Report-scoped organisation identity review

Status: domain, storage and SQLite migration foundation, 7 September 2026.
This is the next E6 slice of the full research expansion plan. Authorised service
and HTTP endpoints are implemented; the report review interface is present with
focused checks. Broader operational acceptance remains unfinished. It does not
introduce a global entity graph.

Revision citations now open and focus matching entries in the displayed frozen
report version's evidence annex. Unknown labels remain plain text; original
excerpts and relations are preserved. The shared navigation provider also serves
claim history. This addition passed 29 focused navigation/annotation tests, type
checks, scoped lint and independent review after the full integration run.

## Decision and evidence

The operator answers whether one captured candidate identifies the subject of
one frozen report version. Outcomes are matched, rejected, unresolved or withdrawn.
A match is an attributed operator judgement, never a source grade, automatic
ownership edge, transitive identity merge or model-training instruction.

The service must derive and freeze the subject from the selected report scope.
Clients choose the existing candidate's evidence label and supply a disposition,
rationale, unresolved disagreements and optional exact supporting/opposing/context
excerpts. They cannot replace the candidate's source metadata or choose scope.
Where the report has no unambiguous subject, the UI must explain the limitation;
it must not silently infer a new subject from the chosen candidate.

New decision snapshots preserve the existing candidate projection and the original
bounded evidence attributes. This retains GLEIF legal names, registration numbers
and jurisdiction assertions absent from historical context projections. Original
context is not rewritten or reprojected. Registry identifiers retain namespaces
and leading zeroes. Unknown issuer/jurisdiction remains unknown.

## Delivery sequence

1. Domain revisions and candidate snapshots: initial implementation present.
   Server-issued IDs, aware time, bounded rationale/conflicts, exact optional
   excerpts and fixed candidate/subject/version anchors are validated. Initial
   withdrawal is rejected; subsequent decisions append history, at most 100 rows.
2. Add strict codec, canonical payload digest and separate root anchored to the
   report version UUID/number and full evidence digest. Reject corrupt payloads,
   duplicate fields and inconsistent history before exposing them.
3. Repository, immutable SQL rows and migration 0026 are present. Scope-filtered
   lists, byte/count aggregation, CAS appends, explicit dependent deletion and
   loss-sensitive downgrade are implemented. Service-level quota enforcement and
   PostgreSQL migration acceptance remain open. Disposable SQLite databases were
   used; no operator database was migrated.
4. Service operations use current session checks, administration guard,
   parent authority and exact evidence anchors. SQL scope filtering precedes
   pagination/counts. Archived teams remain readable, ordinary writes stop, and
   the existing administrator override policy applies.
5. Thin list/create/exact-history/revise endpoints and generated types are present. Add
   Review identity beside frozen candidates, with clearly separate decision history,
   conflict-preserving drafts and account/access-change clearing.
6. Extend deliberate evidence-package selection with exact identity revision IDs;
   do not add current reviews implicitly to historical exports.
7. Verify migration, rollback, stale revisions, quotas, private/team/admin access,
   revocation, multilingual identifiers, unknown jurisdictions, equal names with
   different registrations and unchanged frozen report bytes. Human review must
   assess whether decisions are supported; structural checks cannot establish that.

## Current evidence

Thirteen isolated domain tests passed. They cover preserved script/identifiers,
correction history, changed-anchor rejection, distinct jurisdiction metadata,
unknown/duplicate candidates, initial withdrawal, rationale and exact excerpts.
Mypy passed across 527 source files. Scoped Ruff passed after a test-only literal
formatting repair. These tests are separate from the already-collected full
backend run. No persisted identity review or user-facing delivery is claimed yet.


### Identity review validation and storage codec

Read-only review found shallowly mutable candidate snapshots and unchecked prior
revision structure. Candidate validation now requires immutable typed collections,
known historical context semantics and exact agreement between projected identity
values and frozen source attributes. Correction validation rejects malformed
sequence numbers, predecessor identities, dispositions, timestamps and containers.

Added a bounded canonical storage codec with SHA-256 and byte-count checks.
Decoding revalidates structure and compares canonical bytes, rejecting coercion
(such as boolean revision numbers) and unknown fields even with recomputed hashes.
These hashes detect retained-byte corruption, not source authenticity. All 36
combined domain/codec tests passed; scoped Ruff and mypy (528 source files) passed.
SQL tables, migration, repository and authorised API/UI remain unfinished. The
concurrent full backend run excludes these newly introduced modules/tests.

### Persistence and migration acceptance

Migration 0026 follows the verified 0025 head, registers identity metadata and
adds only the identity root/revision tables. A populated disposable SQLite
database retained account/session rows, report content, frozen evidence and claim
history byte-for-byte across upgrade, empty downgrade and re-upgrade. Alembic
metadata comparison found no differences for either identity table. Downgrade
refuses retained roots or even orphan revisions before any DDL.

Report deletion now explicitly removes its identity history in the caller's
transaction. Repository regressions cover rollback after deletion, unrelated
report preservation, stale CAS, revision-insert failure after pointer update,
duplicate candidate/version rejection, incorrect parent versions and corrupt
revision indexes. Personal visibility is applied before counts and pagination.
Team-scope and authorised service acceptance remain outstanding.

The combined identity suite passed 48 tests; the strengthened populated migration
test then passed all three migration cases. Mypy passed across 532 source files.
Read-only review found no confirmed migration/schema/deletion defect; its two
test gaps were addressed with populated preservation and report deletion tests.
No PostgreSQL run, operator migration or user-facing identity workflow is claimed.

The nine repository tests also passed after explicitly enabling SQLite foreign-key
enforcement for the report-deletion integration test. Seventeen existing report,
claim and CLI/migration regression tests passed. Scoped Ruff and file-length
checks passed. The full backend suite has not been rerun for this migration slice.

### Authorised service and HTTP endpoints

Added `/api/identity-reviews` list/create and `/{decision_id}` read/correct routes,
plus `/{decision_id}/revisions/{revision_id}` for exact historical retrieval.
Successful responses are not cacheable. Strict request bodies reject client-owned
subject, actor, team and candidate snapshots. The server derives the subject from
an explicit company research scope; generic questions without that subject cannot
silently become organisation identity judgements.

Every operation takes the shared administration guard and validates the current
session and parent/root access. Retained candidates and any excerpts are refrozen
against the exact report version, evidence digest and subject. Corrections require
the latest revision ID. Scope limits are 1,000 decisions and 64 MiB of retained
revision payloads; domain history remains bounded at 100 revisions. Decision and
audit writes commit together or roll back together. No model call is involved.

Any current team member can create a review on a shared report. Existing reviews
are readable by other members, but correction requires the author, a global
manager who also leads that team, or an administrator. Each captured candidate has
one review root per report version. Removed members lose access; archived teams
remain readable with the existing administrator write override. Team quota is
shared across authors rather than charged separately to each member.

The combined identity service/storage/migration suite passed 69 tests, followed by
13 HTTP tests. Mypy passed across 536 source files, both import-layer contracts
passed, and scoped Ruff/file-length checks passed. OpenAPI and frontend types were
regenerated; frontend type checks passed. A read-only review found no confirmed
service/API boundary blocker. The API test's incorrect expected 400 was corrected
to the existing 422 invalid-request contract, and a stale admin fixture caused by
MFA enrolment was corrected in the team archive test.

Remaining acceptance includes UI review/history, deliberate identity revision
export selection, wider manager/revocation/failure checks, full-suite coverage and
PostgreSQL integration. Legacy candidate labels can be up to 64 characters, while
the shared optional citation contract accepts 32; such long labels can currently
be reviewed but not cited through that contract. Generated E-number labels fit.

Fifteen existing claim service/API regression tests also passed after route
registration. Full backend coverage has not yet been measured for this slice.

### Report interface

Added an explicit Identity reviews and history section to the report view. It
shows preserved identifiers and aliases, original captured attributes, the fixed
research subject, operator disposition, rationale, unresolved conflicts and exact
excerpts. New reviews choose a captured candidate; corrections fetch the current
root before enabling the editor and append against its exact revision ID.
Historical navigation requests explicit revision IDs and leaves the generated
report unchanged.

The editor retains multiline conflicts as separate original strings, preserves
existing citations and keeps its draft after a stale-save response. Switching
account, access revision, report or report version remounts the section and aborts
its private requests. A read-only review identified pagination discarding an open
draft; pagination, candidate switching and starting another review are now disabled
until save/cancel. Permission/loading failures retain an explicit cancel route.

Ten focused UI tests passed, including history, creation, server-owned field
omission, stale-save draft retention, permission disclosure, account/access/report
clearing and the pagination regression. Before the final pagination repair, 141
report-feature/component tests passed. Type checks and scoped lint passed after
the repair. Real browser visual
acceptance and deliberate identity-revision export selection remain outstanding.

The first full frontend run passed 824 tests but failed its unchanged 90% branch
gate at 89.91%. Added behavioural checks for explicit withdrawal, conflict/excerpt
removal, duplicate excerpt prevention, cancellation and list/detail/history error
recovery. All 13 identity UI tests passed in focused runs. An unnecessary test
type assertion was replaced with a typed query. The production build passed with
the existing chunk-size advisory. Full coverage is being rerun after these tests.

The next full run passed 826 tests and failed one existing TeamRoster viewport
test before coverage reporting. Its single replaceable media-query callback and
immediate assertion were replaced with per-listener subscription tracking and
explicit waits for subscription/render. The three roster tests passed afterwards.
That rerun ended with 807 passes and 20 failures across unrelated interaction
tests, including repeated 15-second timeouts. The roster test then received
explicit listener types and an asynchronous `act` callback to satisfy strict
lint/type checks. The four-worker full run ended with 821 passing tests, two
failures and two worker-start errors in `data/identity-frontend-four-workers.log`.
The Bedrock failure recorded over 33 minutes for one test, suggesting elapsed-time
or process scheduling disruption. The navigation failure occurred while waiting
for the initial heading. No confirmed navigation product defect was found by
static review. All four affected files passed a focused single-worker run
(15 tests). This does not establish a passing full coverage run.

### Selected identity evidence packages

The package API accepts exact identity revision IDs alongside claim revision IDs,
with a combined limit of 20. Each retained candidate and optional excerpt is
validated against the selected frozen report version. Rendering releases the
database transaction, retains the existing bounded worker slots, and rechecks
current access, report content and selected revision content before download.
A later correction does not silently replace an explicitly selected earlier
decision. Claims and identity judgements remain separate records in the ZIP.

Identity-containing packages use manifest v3, retain the original frozen package
files and include selected identity revisions, their source attributes and
integrity hashes. They do not fetch original source files or include unselected
history. Claim-only exports retain their v2 format. The existing route remains
available, with a `selected-evidence-package` alias for combined selections.

The report interface now shares one selection tray across claims and identity
reviews, including historical choices. The combined cap is visible; account,
access, report and version changes clear selections and abort pending downloads.
OpenAPI and frontend types were regenerated. Renderer tests passed 17 cases,
legacy selection/export/API checks passed 21 cases, and the new identity selection
and HTTP checks passed 10 cases. Mypy passed across 537 source files and scoped
Ruff passed. Read-only reviews found no new boundary or selection issue. Report UI
integration passed 91 tests in 20 files, including mixed historical selections,
combined capacity and access-change cancellation. Type checks, scoped ESLint and
the repository file-length check passed. The new test initially compared Blob
constructors across browser/Node realms; it now checks the downloaded filename
and blob content properties. The two-worker full frontend run ended with 829
passing tests and one administrator-login timeout (830 tests, 151 files). All 12
login tests then passed in isolation. Coverage was not reported because the full
run failed; no threshold was lowered. Production build and `git diff --check`
passed; the existing bundle-size advisory remains. PostgreSQL and browser acceptance remain
outstanding. Review also identified an
existing claim-editor draft-loss path through pagination/generation. A subsequent
focused repair now locks those actions during editing, with passing regressions.
The full frontend run including the new relationship view subsequently passed:
95.45% statements, 90.11% branches, 94.2% functions and 96.64% lines. This supersedes
the earlier failed frontend runs, but not the outstanding backend, PostgreSQL,
real-provider and browser acceptance checks.

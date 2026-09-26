# Atomic claims and correction history

Status: domain, SQL persistence, migration 0025, authorised API, operator editor,
revision history and request-driven model proposals were committed in e71a93e.
Automatic report production and selected-revision evidence-package API/UI are now
implemented in the working tree. Final backend regression, browser acceptance and
human-reviewed model-quality acceptance remain open. The working tree is not yet
committed. This extends E7/E9 of the full expansion plan; scoring is unchanged.

## Behaviour to deliver

The automated report pipeline should propose individual attributed assertions
with supporting, opposing or contextual frozen excerpts. A proposed assertion is
not automatically a verified fact or an atomic statement. Operators can inspect
and review each assertion, correct it with an explanation, or withdraw it.
Corrections append revisions; previous statements and evidence remain available.
An unresolved contradiction remains explicit even after operator review.

The current domain contract requires exact original title/summary excerpts of up
to 1,200 Unicode code points. Offsets are code-point based, end-exclusive, with
no trimming or normalisation. Browser UTF-16 selections need explicit conversion.
Each citation freezes the event identity, source content hash and excerpt hash.
Literal presence does not establish semantic support, authenticity or truth.
Statements and correction reasons are bounded at 1,200 characters; a revision
has one to twenty citations and up to twenty explicit unresolved conflicts.

New claims begin as proposed. A review or withdrawal is a separate revision.
Revisions retain claim ID and exact report-version identity and cannot move
backwards in audit time. Persistence must supply server IDs/time, enforce the
latest revision with compare-and-swap and validate the entire frozen evidence
anchor, not rely on the event content hash alone. The domain constructor does
not replace access checks, persistence integrity or semantic review.

## Delivery status and remaining acceptance

| Contract | Current evidence |
| --- | --- |
| Strict revision codec, canonical digests, exact report/evidence anchors | Implemented in the claim domain and persistence, committed in e71a93e |
| Scoped immutable storage, migration, quotas, CAS corrections and ID-only audit | Implemented with disposable SQL tests; no operator migration performed |
| Authenticated editor, review/withdrawal and historical revision navigation | Implemented; UI regressions cover stale edits and access changes |
| Bounded routed model proposals and retained origin | Manual action committed; automatic production integrated in working tree |
| Deliberately selected revisions in evidence packages | Offline renderer, post-render guards, API and UI implemented in working tree |
| Full integration verification | Frontend 802-test full pass plus focused additions; new full backend run ongoing |
| Human-reviewed atomicity, citation support and real configured-model quality | Outstanding; fixture success does not establish these properties |
| Browser visual/keyboard acceptance for the expanded claim/export flow | Outstanding |

The automatic pipeline retains explicit outcomes and original proposal IDs. Later
reviews do not rewrite frozen reports or change scoring. Selected exports preserve
original base-package member bytes and carry separately identified annotations.
Direct account changes clear selection and suppress pending downloads; selection
across pagination keeps exact revision IDs. Eight focused selection/scope tests
passed after adding those review-requested cases.

Remaining work includes closing the running backend check, a coherent reviewed
commit, browser acceptance and the wider human-reviewed benchmark. This status
section supersedes earlier chronological notes that describe then-pending stages.

No percentage of truth or source-grade change is introduced by claim review.


## Internal storage progress

Claim roots now inherit personal/team scope directly from the parent report and
retain the exact report-version UUID. Initial rows require a proposed first
revision; corrections use a conditional latest-pointer update and consecutive
revision number. Earlier revision payloads are retained. JSON payloads have
canonical SHA-256 integrity checks and a 256 KiB per-revision ceiling. This is
corruption detection, not tamper-proof storage or source authentication.

Seven disposable SQLite repository tests passed: round trip, inherited ownership,
stale correction, report/version/sequence/time rejection, payload corruption and
explicit dependent deletion. Type checking passed across 503 source files.
These tests do not establish multi-session PostgreSQL concurrency, scoped listing,
service access controls, migration compatibility or complete quota enforcement.
The repository is not yet wired into the container or report deletion service.


## Migration and storage review follow-up

Migration 0025 adds claim roots and revisions. Disposable SQLite upgrade preserves
accounts; an empty downgrade succeeds, and downgrade with retained claim history
fails explicitly. Report deletion now removes dependent claim revisions and roots
before report versions, including where SQLite foreign keys are disabled.

Storage validates full revision structure in both directions, independently of
hash equality: bounded nonblank text, citations/conflicts, identities, aware audit
time, excerpt offsets/hashes and initial state. Six regression cases reject
malformed objects and payloads even with recomputed matching hashes. Personal
claims retain the parent owner; team claims retain their author for the existing
member-edit policy, while team scope derives from the parent report.

The combined claim/domain/codec/repository/migration suite passed 56 tests before
a validation-helper extraction. Ruff and mypy (503 files) passed afterwards.
PostgreSQL migration/concurrency, application authorisation, evidence-anchor
verification and scoped quotas remain required before exposure.


### Claim application service and quota enforcement

Wired a session-scoped ReportClaims service and repository port into the container.
Create, read and correction operations validate the current refresh family and
security version under the administration guard, check parent/claim scope and
revalidate exact frozen evidence/citation anchors. Corrections retain their root
version and use conditional appends. Limits are 1,000 retained claims and 64 MiB
per personal/team scope, with 100 retained revisions per claim; withdrawn history
continues to count. Audit entries contain action and report/claim/revision IDs,
not private statements or excerpts. No automatic grading changes occur.

Eleven combined service/repository tests passed before adding access cases. The
expanded eight-case service group passed, including stale-session rejection for
create/read/update, foreign personal scope, quota failures, old-revision reads,
stale correction rejection and unchanged frozen report content. Ruff and mypy
(506 source files), file-length and diff checks passed. Review is pending. API,
scoped lists, editor, automatic proposals, full team/revocation/concurrency tests
and PostgreSQL acceptance remain unfinished. No operator migration or deployment.


### Claim HTTP and scoped listing

Added /api/claims create, conditional correction, current/exact revision reads
and frozen-version listing. Pages contain at most twenty claims; visibility is
filtered in SQL before counts/limits and the service rechecks parent scope and
evidence anchors for each returned item. Responses use no-store. Request schemas
reject extra audit fields, boolean offsets, unsupported source fields and oversized
text/link collections. Exact excerpt mismatches are rejected by the domain service.

Six HTTP tests passed, covering immutable history, stale correction conflict,
bounded listing, malformed input and foreign personal scope. OpenAPI and frontend
types were regenerated; frontend type checking, scoped Ruff, backend mypy (508
files), file-length and diff checks passed. Earlier service review found no
confirmed access/quota blocker. API/list review is pending; the editor, automated
proposals and broader team/concurrency/operational acceptance remain unfinished.


### Claim viewer and API review follow-up

The report page now offers an on-demand claim annotation viewer with exact
revision history, bounded pagination, original supporting/opposing excerpts,
review states and unresolved conflicts. A shared scoped-request hook aborts
requests across account/access changes; the existing map hook re-exports it.
Claim data remains outside browser persistence. Creating/editing claims in the
UI and automated proposal generation remain unfinished.

API review identified oversized version integers reaching SQL binding. Schema,
query and service now enforce the signed 32-bit range, with an HTTP regression.
Listing computes the frozen evidence digest once per page while still checking
each claim root's scope/version/anchor. Seven claim API tests passed and two
viewer tests passed for lazy loading, exact selected version and explicit errors.
OpenAPI/types were regenerated. Mypy (508 files), file-length and diff checks
passed. Frontend type checking passed before the final viewer formatting change;
ESLint identified non-null assertions, which were replaced with explicit guards.
Broader history/access UI acceptance and final integration checks remain open.


### Operator claim editor

Added the report-page editor for proposed claims and appended review/correction/
withdrawal revisions. It collects one assertion, type, original supporting/opposing/
context excerpts, explicit conflicts and a required reason. Existing claims load
latest root/revision permissions before editing; server-side authority and CAS remain
mandatory. The editor retains at most twenty citations and does not alter prior
report bodies, judgements or source grades.

The excerpt picker uses selection in a read-only captured title/summary field,
including keyboard selection. UTF-16 browser offsets convert explicitly to Unicode
code-point offsets; split surrogate pairs and oversized/blank excerpts are rejected.
Four focused UI tests passed for viewer states, Unicode locator conversion and
proposed-claim submission. Frontend type checking passed after integration; scoped
ESLint passed after explicit code-point conversion and test assertion repairs.
File-length and diff checks passed. UI review, correction/conflict/access regression
coverage, visual acceptance and automated model proposals remain outstanding.


### Claim editor review repairs

Read-only UI review found textarea CRLF/CR normalisation could shift original
excerpt offsets, and controls remained editable during a pending save. The picker
now renders normalised textarea text and maps selection boundaries back to the
unchanged raw field. Mounted CRLF/CR regressions initially failed due to controlled
textarea caret reset; rendering the normalised value fixed that remaining issue.

The editor disables its entire fieldset while saving, uses one captured abort
signal and checks it before completion callbacks. Ten focused UI tests passed,
including Unicode/newline locators, proposal submission, withdrawal against an
exact base, stale-edit retention, access-change draft clearing and suppressed
completion after unmount. Broader frontend regression and final static checks
are next. No automated claim-generation completion is implied.


### Claim integration regression and coverage follow-up

The combined backend claim suite completed with 71 passes. The full frontend
suite completed with 785 passing tests in 140 files, but failed the existing
branch-coverage gate: 89.45% branches (90% required), 94.81% statements, 93.15%
functions and 95.98% lines. This is not a passing full verification.

Added real API-client workflow tests for exact revision navigation, pagination,
current-root edit permission, denied permission, failed revision loading and
appending a review. Four workflow tests passed after correcting a mock response
to return frozen citation records rather than editable citation inputs. The
pending test-only require-await lint issue was repaired. A new full frontend
coverage run is required; thresholds remain unchanged. Automated claim proposals
and broader operational acceptance are still unfinished.


### Full frontend coverage passes; model-proposal validation starts

The full frontend rerun completed successfully: 789 tests in 141 files passed,
with 95.43% statements, 90.05% branches, 94.05% functions and 96.62% lines. The
existing 90% branch gate is unchanged. The frontend production build also passed.

Started the model-proposal boundary with a bounded parser: at most twenty distinct
assertions, five original-field citations each, explicit conflicts and known claim
types. Locators derive from unique verbatim occurrences in frozen evidence;
invented, translated-field, ambiguous, duplicate and instruction-like proposals
are rejected. Model output cannot mark itself reviewed. Ten parser tests passed;
Ruff and mypy (509 files) passed. This parser is not yet connected to a model call,
provenance record, automatic report generation or persistence. Those integration
steps remain part of the full objective. All claim changes remain uncommitted.


### Bounded claim-proposal model call

Added a one-call gateway function around the strict proposal parser. It uses the
selected profile's provider/model/reasoning settings, a 45-second deadline and
bounded input/output (100 evidence records, 256 KiB prompt, 128 KiB response).
Original evidence and saved judgements are untrusted prompt data. Duplicate JSON
keys and invalid proposals are rejected; cancellation propagates without retry.
The result distinguishes completed, empty, invalid, unavailable and unsupported
input, and retains profile revision, requested/returned model, input hash and usage.

Nineteen model/parser tests passed. An oversized parametrised fixture initially
exceeded Windows test-path handling; explicit short case IDs repaired that test
setup. Ruff, mypy (510 files), file-length and diff checks passed. No real model
call was made. Pipeline/API admission, provenance persistence, automatic report
proposal creation and operator-facing generation remain unfinished; this is an
internal gateway boundary, not end-to-end automated claim delivery. Review pending.


### Immutable model-origin metadata

Added optional model-origin metadata to claim revisions: batch/profile IDs,
profile revision, provider, requested/returned model, exact input digest, method
version and generation time. It validates before storage and survives operator
corrections; a correction cannot replace the originating model record. Client
claim-edit schemas still forbid caller-supplied origin. Claim history can display
the retained provenance, and API types have been regenerated.

Fifty combined origin/codec/domain tests passed, followed by sixteen origin/model
cases including duplicate-label input rejection before any model call. Four UI
workflow tests passed with provenance presentation. Ruff and mypy (511 files)
passed. Frontend type checking passed after aligning optional wire metadata with
the client's normalised null and declared generated response types. File-length
and diff checks passed. Automatic generation admission and origin-aware batch
persistence are still pending; no actual model proposals were stored or generated
against an external provider. The full objective remains active and uncommitted.

### Proposal admission and atomic persistence

The claim service now prepares an authorised report snapshot and commits before
returning, releasing database guards before external model work. Persistence
rechecks the current session, parent scope, creation permission, exact version,
evidence digest and report-body digest. Independent immutable identifiers and
digests prevent mutations of the model-input object from changing the admission
anchor. Every proposal is validated and aggregate count/byte capacity checked
before any writes; storage or audit failure rolls back the entire batch.

Eight batch tests cover transaction release, durable proposed-state provenance,
quota rejection, stale sessions, changed evidence, mutable version/body rejection,
invalid final proposals and failure on the second write. The combined batch and
existing service group passed 16 tests. Seven origin tests passed, including
2,048-character provider model IDs. Mypy passed across 512 source files; scoped
Ruff and formatting checks, file-length and diff checks passed after formatting
repair. The current claim service is 348 lines and should be split by responsibility
before further expansion. Model orchestration, usage accounting, API/UI generation,
automatic report integration and broader operational acceptance remain outstanding.

### Request-bound generation and operator action

POST /api/claims/generate now uses the report's current team/global model assignment,
releases routing transactions before calling the provider, and retains provenance
on validated proposals. Admission permits two attempts per report version, six per
user and thirty globally per hour. These are separate model-call limits; no source
collection runs. Usage records include observed token counts and generic outcomes,
and survive later authorisation/quota rejection. Unsupported input makes no model
call and has no usage row.

The endpoint watches for ASGI disconnects and cancels/awaits model work before the
request session closes. Cancellation attempts bounded usage accounting with unknown
tokens, then propagates. A disconnect during commit still has an indeterminate
outcome; the response advises checking history before retrying. Twenty-one combined
generation/batch/API tests passed, including a simulated disconnect during a blocked
gateway, transaction release, and no partial proposals.

The report claim panel offers Generate proposed claims, discloses provider input
and token use, disables pending submission and reports completed/empty/invalid/
unavailable/unsupported results separately. Scoped aborts suppress stale completion.
Thirteen generation/viewer/workflow UI tests passed. Frontend type checks and scoped
ESLint passed. Backend Ruff, mypy (514 files) and both architecture contracts passed.
OpenAPI and client types were regenerated. Full backend/frontend suites are running;
no final full-suite result, real provider call or deployment is claimed here.
Automatic invocation in report production and stronger human-reviewed quality
acceptance remain required by the full plan.

The full frontend generation run passed 795 tests in 142 files: 95.39% statements,
90.05% branches, 94.02% functions and 96.57% lines. Coverage thresholds are unchanged.
The full backend run remains active, with its output in the local ignored
data/claims-backend-full.log; do not interpret focused passes as its final result.

Automatic production integration must use the run's frozen RoleProfiles and perform
the claim model call before Producer's before_persist callback acquires write guards.
Proposal persistence should follow the report/version insert in the same transaction,
with aggregate quota checks and a recorded outcome when proposals cannot be saved.
Calling the manual generation API after report completion would re-resolve routing
and does not fulfil this contract. Request, regeneration and scheduled production
need equivalent behaviour under their existing authority policies.

### Automatic production stage and outcome contract

Added an isolated automatic proposal stage accepting the existing frozen profile
lookup. It has no repository writes and returns a transient pending batch with
fixed report/version identifiers, original body/evidence digests, initial revisions
and buffered model usage. It shares user/global proposal admission with manual
generation. Concurrent profile edits do not change the selected model. Unsupported
inputs and missing models make no provider call; unavailable calls do not invent a
returned-model provenance record. Invalid proposals leave an explicit failure outcome.

The new schema-1 ClaimGenerationReceipt distinguishes completed, empty, invalid,
unavailable, unsupported, no-model, rate-limited and quota-exceeded outcomes. Successful
receipts retain exact initial revision IDs and validated model provenance, allowing
later operator annotations to remain separate. Unknown fields, malformed identities,
duplicate revisions, false success and unsupported schema versions are rejected.
Legacy reports without a receipt will mean not recorded, not successful emptiness.

These new modules are not yet wired into Producer or ReportVersion persistence.
The existing full backend run continues against its previously collected suite;
covered production files were left unchanged while it ran. All 22 focused
stage/receipt tests passed, including missing-model/unavailable-provider outcomes.
Mypy passed across 516 files; scoped Ruff, formatting, file-length and diff checks
passed. Integration review confirmed
that scheduled and indicator reports already use GenerateReportUseCase.execute,
so the shared Producer stage is the required integration point for all paths.

### Automatic transaction participant

Added AutomaticClaimStorage as a transaction participant, not an independent
committing use case. It revalidates actor/report/version, frozen body/evidence and
exact original citation anchors, checks aggregate retained count/bytes, and converts
insufficient capacity to a quota-exceeded receipt with no selected revisions.
Initial claim writes and ID-only audits follow parent insertion; exceptions propagate
for the caller to roll back the complete report transaction. ProductionResult now
explicitly carries a version and optional pending claims rather than hiding transient
state on a persisted domain object.

Five disposable SQL storage tests passed: caller rollback, count/byte capacity
rejection, failure on the second claim and changed-anchor rejection. Mypy passed
across 517 files before adding the small ProductionResult value object; scoped Ruff
and formatting passed. These tests prove the participant is rollbackable, not yet
that the full report pipeline uses it. The previously started full backend suite
is still active. Producer, generate/save orchestration and receipt persistence
remain the immediate integration work once that baseline finishes.

### Checked claim milestone baseline

The full collected backend suite completed successfully: 2,557 passed, 14 skipped,
95.12% coverage against the unchanged 90% gate. The automatic receipt/stage/storage
modules were added after collection; their 22 stage/receipt and seven SQL storage
tests passed separately. Storage coverage now includes new report/version plus
first-claim rollback when the second claim fails, and administrator generation
charging the personal report owner's quota. These remain component-level checks,
not proof that the report producer invokes this stage.

Full backend Ruff passed and all 808 checked Python files were formatted. Mypy
passed across 518 source files. Configured Bandit and both architecture contracts
passed, as did file-length and diff checks. Frontend verification remains the
795-test full pass at 90.05% branch coverage and successful production build;
Prettier repaired formatting in the claim workflow fixture. No operator migration,
external model call, deployment or remote push was performed. The next integration
must wire automatic proposals and receipts into Producer and the report transaction.

### Automatic report pipeline integration

Producer now has an explicit ProductionResult path. After the final challenge,
redraft and evidence-link resolution, it runs the automatic proposal stage with
the frozen assessment-profile lookup. Model usage is buffered and included in
report token/latency totals before the final authorisation callback and SAVING
stage. Unsupported inputs are preflighted before either manual or automatic
provider-call allowances are consumed.

SaveProduction performs fresh current/background access checks and retains a single
transaction for report/version insertion, quota-admitted initial claims, usage and
audits. A failed claim write rolls everything back. Quota rejection freezes a
quota-exceeded receipt with no revision IDs before the report is serialised.
ReportVersion stores optional schema-1 receipts in its existing analysis JSON;
legacy records remain absent. The report API and UI now present that outcome
separately from mutable annotations and scoring. No additional migration beyond
the already required claim migration 0025 is introduced.

Eight initial pipeline/report tests passed, covering actual creation/regeneration,
the schedule factory, durable receipt reload and full report/usage/claim rollback.
Four additional pipeline security cases passed: account deactivation and team-member
removal during the model call, cancellation before persistence, and persisted
quota-rejection provenance. Automatic cancellation follows the existing production
policy: buffered usage is not persisted when the whole report is cancelled; no
zero-cost assertion is made. Manual request cancellation has separate attempt accounting.
Seventeen focused UI tests passed before a formatting/type refinement. Mypy (520
files), full backend Ruff, configured Bandit and frontend type checks passed.
Broader affected backend tests and the full frontend coverage run are in progress.
The preceding full backend 2,557-pass baseline predates this integration.

### Integration verification follow-up

The affected backend group finished with 407 passes and six routing-fixture
failures. Each failure was the scripted gateway lacking the newly invoked
claim_proposals schema. The fixture now returns valid proposed claims; assertions
verify destination routing and retained claim provenance across mid-run binding
changes. All eight routing integration tests then passed. This is broad verification
plus targeted repair, not a second clean run of the whole affected group.

The full frontend suite passed 799 tests in 143 files, with 95.39% statements,
90.06% branches, 94.02% functions and 96.57% lines. Production build passed with its
existing chunk-size advisory. ESLint, frontend type checking, full backend Ruff,
mypy (520 files), configured Bandit, architecture, file-length and diff checks passed.
The new full backend run is active in data/automatic-claim-pipeline-backend-full.log.
No real configured-model evaluation, migration of the operator database or deployment
has occurred. Pipeline integration changes remain uncommitted pending that run.

### Selected claim evidence package foundations

Added an offline v2 package renderer for one to twenty explicitly selected claim
revisions. It preserves the base package member bytes, retains the original
manifest separately and records selected revision IDs and integrity hashes. It
fetches no original assets or source URLs. A shared aggregate uncompressed size
limit covers the base content and added claim records.

The selection service resolves exact authorised revisions, releases read
transactions before rendering and rechecks current session and parent access
before delivery. New corrections do not silently replace the selected historical
revision. Fourteen combined selection/renderer tests passed; an additional real
team-membership revocation regression then passed in the six-test selection suite.
Scoped Ruff and mypy across 522 source files passed. Endpoint, shared render
admission and UI integration remain unfinished, and review is pending. The full
automatic-pipeline backend suite is still running; these newly added tests are
outside its previously collected test set.


### Selected claim download integration and verification

Added POST /api/reports/{report_id}/claim-evidence-package with strict explicit
version/revision selection, no-store download headers and regenerated OpenAPI/client
types. The exporter shares the existing two-worker package allowance, preserves
admission through cancellation and rechecks access and report-content integrity
after compression. Whole record/version hashes deliberately reject concurrent
metadata changes, including regeneration; retry against the selected version.

Read-only review found no confirmed access blocker. Its mutable-render-input gap
was repaired and the cancellation test now waits for both admission slots to recover.
All 24 combined selection/renderer/use-case tests passed; the five use-case cases
passed again after deterministic cancellation cleanup. Six new API tests passed.
Backend Ruff and mypy (526 files), generated frontend types and frontend type checks
passed. The selection/download UI remains unfinished.

The full automatic-pipeline backend run completed with 2,590 passes, 14 skips and
three stale direction-stage fixture failures, at 94.94% coverage. These fixtures
required new claim-stage order, token/latency and usage-purpose expectations.
Targeted repairs are being verified; this is not a clean full-suite pass.

The repaired direction/plan and new export API group subsequently passed all
14 tests. This is the full run plus targeted repair evidence, not a second
clean full run. File-length and diff checks also passed.


### Selected claim package interface

The claim panel now supports selecting exact current or historical revisions,
reviewing/removing the selected list and downloading the v2 evidence package.
Selection is limited to twenty revisions and stays in memory. Account, access,
report and version changes remount the panel, clear selection and abort pending
downloads. Failed downloads retain selection for retry. Claim history rendering
was extracted into its own module to keep responsibilities and file sizes bounded.

Ten focused UI tests passed, followed by the full frontend suite: 802 tests in
144 files, 95.35% statements, 90.02% branches, 94.02% functions and 96.58% lines.
Production build passed with the existing chunk-size advisory. Three additional
selection-limit/report/version tests passed after full-suite collection. Read-only
review found no confirmed blocker and identified further account/pagination test
coverage opportunities. The export test root version was aligned with the rendered
version. No browser visual acceptance or real provider test is implied.

A subsequent full backend run completed with 2,623 passes, 14 skips and 94.46%
coverage in data/claim-export-backend-full.log. This predates identity review and
combined export additions and is not current full-backend acceptance.

### Claim draft protection

Claim pagination, generation and opening another editor are disabled while a
draft is open. A generation request also prevents opening a draft or changing
pages until it settles. The existing-review permission/error state now offers a
cancel route so the edit lock can be released. A failing pagination regression
was reproduced before the repair; 11 focused claim/generation tests passed after
the fix. Access invalidation still clears private draft data. Full frontend
integration passed with the organisation relationship view: 95.45% statements,
90.11% branches, 94.2% functions and 96.64% lines. Production build passed.

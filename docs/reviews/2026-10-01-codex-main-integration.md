# Codex integration with current main, 1 October 2026

The coordinator fetched main at `9ae40e3d0de91069a22fc6c8eb81777e7e8d9518`,
including Claude's merged PR 116. The nine Codex PRs remain a dependency stack;
their earlier successful CI does not validate this newer combined source.
The primary checkout's prepared changes remain untouched.

## First branch checkpoint

PR 88 merged current main without textual conflicts. Its user/admin input-role
contract and legacy output compatibility remain intact. Fresh backend OpenAPI
export and frontend generation match the merged files byte-for-byte.
Frozen backend/frontend installation succeeded, retaining main's PyJWT,
urllib3 and axe-core updates. Both frontend TypeScript configurations pass.
The focused role/personal-data group passes five cases; the overlapping
role/team/invitation/admin integration group passes 29 cases. Changed Python
Ruff checks and whitespace validation pass. Fresh full CI is still required.

## Architecture branch checkpoint

PR 89 integrated parent `9634f824ea3ab9ae18cc928427028115ede8ae73`
through an ordinary merge in its clean, isolated architecture worktree. Git
reported no textual conflicts. Review confirmed that main's direction-plan,
evaluation, citation-verdict, report-copy and bell wiring remains composed
alongside the named container initialisers and typed report/subscription
boundaries. Evaluation cancellation and draining remain ahead of client and
database disposal. No production-code repair was needed at this checkpoint.

The first combined group passed 146 tests covering application lifecycle,
migration imports, annotation resolution, feed scheduling, report/challenge
production, evaluations and subscription/retry boundaries. A second group
passed 54 existing tests covering the newly integrated feature APIs. Two new
regressions pass through actual container disposal during a scripted evaluation
call, checking the saved interruption and partial artefact before HTTP/database
closure, both with and without a failing HTTP close callback. Their first run
failed because the test tried to replace a read-only engine instance method;
the corrected, scoped class-method patch passed both cases. An earlier command
named two non-existent test modules and ran no tests; the corrected selection
provided the 54 existing-case results. All tests used private in-memory SQLite,
with inherited ASE database/race/PostgreSQL variables removed, and no live calls.

Frozen backend/frontend installs succeeded. Mypy passed for 1,458 source files;
source Ruff lint/format checks, the new test's lint/format checks, all three
import contracts, scoped repository-configured Bandit, file-length checks
(existing warnings only) and whitespace validation passed. A fresh OpenAPI
export and regenerated TypeScript match the merged contracts exactly. Both
frontend TypeScript configurations passed with the bundled Node 24.19.0 runtime;
the initial shell's older Node was replaced for these final checks.

These are focused checks, with coverage disabled rather than a changed gate.
Full combined CI, PostgreSQL validation and independent integration review
remain required. No push, main merge or production operation was performed by
the architecture integration worker.

## Runtime branch checkpoint

PR 90 integrated the reviewed architecture parent `fad1327f` by an ordinary
merge. The router import conflict retains both administration modules; OpenAPI
and TypeScript were regenerated from the actual combined application. The large
generated diff adds the existing Codex error-envelope response contract to main's
new routes. Runtime, phased shutdown, evaluation disposal, request logging and
private stream/bell checks passed 70 cases. Lifecycle, feed-health logging and
stream resume/replay/encoding passed another 74 cases. The first command for
this second group named a missing lifecycle module and ran no tests; the corrected
selection produced the 74-case result. Three focused frontend runtime/request-ID
cases passed. Both TypeScript configurations, source Ruff lint/format, strict
mypy (1,469 files), three import contracts and whitespace checks passed.
Independent read-only review found no actionable integration findings: all
321 parent API operations remain, the runtime endpoint is added, retained
component schemas are unchanged and stream/bell authorisation is preserved.

PR 88's new full CI run `36922277772` completed successfully, including all
SQLite/PostgreSQL lanes, frontend, image and security checks. PR 89's new CI
remains in progress. These results do not establish completion of later batches
or authorise a production merge.

## Security branch checkpoint

PR 92 integrated the CI branch's checked merge milestone `5dd6255a` by an
ordinary merge. Its only textual conflict was the Caddy CSP: main's complete
policy is retained with the Codex reporting directives and endpoint added.
Main's image-package/research/map-view limits and Codex avatar/workspace caps
are retained together. The privacy migration is now 0082, following released
0081, and the current invitation operations guide uses that revision.

Fifty backend cases passed, including actual fresh SQLite CLI migration and
encryption rotation; one real Unix-socket case is skipped on Windows. Eleven
invitation UI cases and nine Caddy policy cases passed. Frozen installs,
source Ruff lint/format, strict mypy (1,475 files), both TypeScript configurations,
three import contracts, deployment/SBOM Actionlint and whitespace checks passed.
Regenerated OpenAPI/TypeScript match the merged contracts exactly. Independent
read-only review found no actionable findings in CSP, stream/bell authority,
invitation receipts, rotation inventory or operational defaults.

PR 89's fresh full CI run `36923838968` succeeded at `fad1327f`. The CI branch's
later frontend coverage additions and full combined measurement are pending;
PR 92 is not yet published at this checkpoint. Real credential rotation,
production operations and main merge remain unperformed.

## Performance branch checkpoint

PR 93 integrated checked security parent `1b48b8b0` by an ordinary merge.
The report-job import conflict retains the validated payload cache and main's
filtered cursor pagination. The reviewed compact polling candidate replaces
payload JSON parsing in listings with validated materialised summaries. Migration
0083 follows invitation privacy 0082 and derives origins only after original
checkpoint validation. Main's shipped migration bytes are unchanged.

The first source lint run found two identical `list_page` methods introduced
by combining main's new method with the candidate; one duplicate was removed.
The combined polling/storage/API/actual-migration group passed 121 cases, and
store/shared-read/stream/bell integration passed 39 cases. Source Ruff lint/format,
strict mypy (1,488 files), three import contracts and both frontend TypeScript
configurations passed. Regenerated API contracts match the merged files exactly.
Independent read-only review found no actionable integration issue in store
invalidation, access-bound payload caching, lease fencing or projection backfill.
These are focused checks, with coverage disabled, not performance measurements.
Full current-source CI, final PostgreSQL migration/model parity and the CI
branch's pending coverage additions remain required before publication.

The runtime branch's full run `36924455345` found one test incompatibility on
both database engines: an equality assertion includes distinct per-request IDs.
The privacy response comparison and response-ID checks are being repaired;
runtime production behaviour is not being weakened to satisfy that assertion.

## Reserved integration work

Current main's shipped migrations retain their existing history through 0081.
Only the unmerged Codex migrations will be re-keyed after that revision:
0082 privacy receipts, 0083 projections, 0084 feedback, 0085 frozen ratios,
0086 reminders, 0087 delivery, 0088 routing and 0089 push. Their downgrade
barriers remain intact. Fresh and existing-0081 upgrade rehearsals are required.

Review found additional integration work in report-job pagination, conditional
indicator updates, alert forms/acknowledgements and report/team-copy boundaries.
Main's measured frontend branch coverage is below the Codex 92 percent gate;
new combined coverage and meaningful regressions are required. Earlier evidence
is retained as historical evidence, rather than presented as current acceptance.

KAN-2, KAN-4 and KAN-144 are Done for their completed non-code deliverables.
Code, operator, performance and elapsed-time acceptance remain separate.
No main merge or production deployment has been performed by this integration.

## Final combined-source reconciliation, 1 October 2026

The reviewed source checkpoint is `68af50a1` on notification PR #96.
Current main remains `9ae40e3d`; the primary checkout and its prepared edits
remain untouched. All nine batches incorporated main by ordinary merges.
Published history was not rebased or force-pushed.

PRs #88 through #93 pass fresh full CI and are ready for review. Their runs are
36922277772, 36923838968, 36927813271, 36930619530, 36931665034 and 36931692903,
respectively. The runtime's request-ID test incompatibility was reproduced and
repaired without weakening its exact stable privacy response checks.

PR #91's complete local frontend run passed 4,292 cases with one existing skip.
Raw JSON and LCOV agree at 22,754/24,694 branches (92.14%); auth 95%, global 92%
and eligible-file 70% gates pass. The retained diagnostic run remains a failure,
separate from this result. See the final frontend validation record.

The first PR #94/#95 combined runs found the same single stale alert-rule
payload expectation. Coverage was 92.11% and 92.15% respectively, with all policy
floors passing, but those test runs failed. A failing local reproduction preceded
the exact-payload repair: legacy defaults and non-default baseline settings are
both asserted. PR #94 is now `2097eb3b`, with 23 focused helper/ratio cases and
both TypeScript projects passing. PR #95 normally merged that repair at
`a45ae032`; all eight helper cases pass there. Fresh full CI runs 36933344519
and 36933445271 validate these repaired heads. The obsolete failed-head runs
were cancelled after their failure and raw coverage evidence were retained.

The source/export integration additionally repaired the generated STIX header
on team copies: only the canonical wrapper is rebound to the currently authorised
report/version. Substantive text, citations and stored Markdown remain unchanged.
Current release fences and filtered map selection are retained. Independent
final security review found no actionable issue.

### Notification and migration verification

Notification integration preserves main's bell schema separately from the new
`AlertWebhookDestinationOut` contract. Main's confirmation, revision, edit/resume,
subscription and membership boundaries remain intact. A reviewed routing defect
now offers an explicit, disclosed reload after a concurrent revision conflict.
Stale mutations are disabled; current scope and authority are fetched together.
Six routing cases and the final combined routing/helper group of 14 cases pass.
Focus retention/restoration was not independently asserted.

The combined Alembic graph has 79 revisions and one head, 0089. Released
0075 through 0081 are byte-identical to main. Unmerged Codex revisions are
0082 privacy, 0083 projections, 0084 feedback, 0085 ratios, 0086 reminders,
0087 delivery, 0088 routing and 0089 push.

All 21 actual SQLite/PostgreSQL history cases passed: fresh and populated 0081
upgrades, whole-model metadata parity, preserved payload bytes/digests/summary
bounds, derived origins, corrupt-prefix repair/retry and retained-data downgrade
barriers. Review then found a test-harness cancellation gap. The helper now joins
the migration thread before fixture cleanup, including repeated cancellation.
Four failing regressions preceded the fix; six cancellation/cooperative cases
and six representative real history checks pass after it. Production migration
bodies were unchanged by that repair.

Thirty-three private PostgreSQL scope/opt-out/bell/rotation checks and all three
concurrency parameters pass. The initial broad SQLite run had one stale rule
revision fixture failure and three PostgreSQL-only skips; subsequent focused and
PostgreSQL runs resolve those four cases. Frontend integration passed 161 cases
across 35 files, followed by 80 cases after the late parent and 14 after the final
routing/helper merge. Counts overlap and are not an overall distinct-test total.

Ruff/format, strict mypy (1,578 source files), three import contracts, Bandit,
file-length gates, lockfile/dependency checks and actual API regeneration passed.
Both TypeScript configurations and changed lint/format passed on the final source
checkpoint. Security review found no actionable finding; runtime and quality
reviewers independently closed the two repairs. See the final notification
integration record for evidence identities and limitations.

Owned PostgreSQL child databases, the labelled container and credential files
were removed after verification. All data and transports were synthetic/mocked.
No real message, production migration or key rotation occurred. Full CI on the
published final notification head remains required.

### Acceptance and release boundary

Jira now has 57 open non-epic items and 11 open epics. KAN-1, KAN-2, KAN-4 and
KAN-144 are Done for verified non-code deliverables. Code tickets require their
acceptance criteria and authorised merge before Done.

Independent reconciliation confirms KAN-43's earlier 100,000-event local Compose
rehearsal satisfies its local criteria: stop 3.654 seconds, exit zero, seven phases,
fresh final snapshot and full restoration. KAN-44 still lacks the required
three-second reference-host SIGTERM-to-ready improvement. The 9.7167-second
historical observation measures start-to-ready and is not that comparison.

The current PR #91 PostgreSQL whole-job total is 2,370 seconds (39.50 runner
minutes), above the 30-minute target. Five comparable observations, the controlled
frontend timing target, consecutive main runs and weekly dependency observations
remain separate criteria. Backup/provider-key changes, policy choices and real
source/transport acceptance remain explicit in the delivery register.

No main merge or production deployment occurred. The repository's required
release approval still applies. Pending workflow outcomes are tracked in the
live PR descriptions and Jira handoffs, rather than inferred from old runs.

## Approved release and manual readiness acceptance, 2 October 2026

Alex explicitly approved merging PRs 88–96 in order. PR 88 merged as
`1d924272785030d4ef8914b5b39ca20762ed0028`; its main CI run `36978697172`
passed. Production deployment remains subject to the existing protected manual
rollout gate and private operator runbook; no successful rollout is claimed.

KAN-42's manual local acceptance passed on PR 90 source `f1a32e17`. A standalone
actual ASGI application/lifespan, FeedScheduler, SystemClock and monotonic clock
used private empty SQLite databases and one synthetic connector, with network
connections blocked. With a two-second cycle and six-second overdue threshold,
readiness was initially 200 after two real cycles. Cancelling the actual scheduler
task produced generic 503 after 5.462 seconds, 6.002 seconds since its last
progress. Only that scheduler was overdue. With feeds disabled, readiness stayed
200 after 6.317 real seconds and scheduler/feed workers were excluded. No network
or message attempts occurred. Both private databases were removed; no owned tasks
or ports remained. The standalone script, log and machine-readable report are
retained outside Git in `runtime-kan42-manual-20261002-actual-clock` beside this
worktree. This completes the manual criterion; Jira closure still requires the
approved PR 90 merge and its fresh integration checks.

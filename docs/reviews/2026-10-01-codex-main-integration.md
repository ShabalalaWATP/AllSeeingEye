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

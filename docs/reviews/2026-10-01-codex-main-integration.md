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

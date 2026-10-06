# KAN-81 conflict control derivation

The conflict hook previously repeated its classification and filtering over the
same current event array. `deriveConflictScope` now derives raw control metadata,
eligible group counts and ordered displayed rows in one full-input traversal.
Source choices retain the existing helper over conflict records. Each invocation
uses fresh local data; there is no persistent cache or event mutation.

The existing display, historical, review and group predicates remain unchanged.
Raw source/history/unreviewed counts retain their original scope. Eligible counts
still precede the selected group. Non-conflict rows, duplicates, input order,
current object references and selection clearing are preserved. The hook memo
includes every input and filter choice.

## Evidence

The unchanged d07867cb baseline passed 16 equivalence cases and failed the intended
work-budget regression: 128 screening-field reads against a limit of 96 for 32
constant-return accepted records. The candidate passed 88 cases across 11 files,
including corrections, expiry, review/category/source changes and selection.
Scoped ESLint and Prettier, both full TypeScript configurations, the production
build and unchanged bundle budgets passed. Initial/globe gzip bytes were
202,528/806,915 against 245,760/870,400 limits. Both independent reviews were clear.
All 12 owned commands closed with empty process groups and closed handles; nine
protected fixture, dependency and benchmark pins remained unchanged.

Source manifest SHA256:
`ce2f568dca55095e0038ef97b0a4b70c067e9e7f88ee7ece29997b25fe7fc003`.
Complete patch SHA256:
`486e536070aaa7d827fa8353c83a01fafe70cec2d01dbd6fdcdd160a8c09d4eb`.
Result SHA256:
`6e359ba732e06eb72765a9e0b9b86c12c649733bd8c96dd1e194d0e2eae41fe5`.
Private evidence lives under the isolated `kan81-conflict-derivation` worktree's
`evidence/derivation-v1`; it is not committed. A Windows evidence-sealing decoding
failure and its explicit UTF-8 repair are retained. Source checks were not rerun
or rewritten to hide that failure.

## Limits

The work-budget regression measures classification reads, not elapsed latency.
This milestone has no new coverage or canonical/browser performance measurement.
The previously completed Linux reference missed the targets for three scenarios,
with new-record latency worsening. KAN-81 remains open for sustained-update and
browser acceptance. Fresh published-head CI is required before release.

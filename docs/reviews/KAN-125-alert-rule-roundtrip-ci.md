# KAN-125: alert-rule round-trip CI repair

Recorded 1 October 2026 against PR #94 base
`3b1f1c922720bd0689bec79e4d930bdeb9adf2e1`.

## Finding and repair

CI run `36931724508` failed the exact request comparison in
`frontend/src/lib/alertRules.test.ts`. The focused local reproduction failed the
same case, with six other cases deselected. The only unexpected fields were the
valid `baseline_ratio: null` and `baseline_days: 30` defaults.

The saved-field conversion and request builder intentionally carry the optional
ratio and baseline window through edits. The original fixture predates those
fields, so its request uses the documented defaults. Production behaviour did
not need changing.

The repaired test keeps exact full-request equality and every previous assertion.
Its two cases check legacy defaults and a saved ratio of 2.5 over 14 days with a
60-minute window. The second case prevents a builder which always substitutes
default baseline settings from satisfying the test.

## Validation

The complete alert-rule helper test file and the ratio update/validation test file
passed all 23 cases in 3.30 seconds using the checkout's private dependencies and
Node 24.19.0. The initial focused reproduction failed as expected.
Both TypeScript projects, changed-file ESLint, test/document Prettier and
`git diff --check` passed.

No production code, generated contract, coverage threshold or security boundary
changed. Coverage was not collected by this focused rerun; a fresh full CI run
remains separate evidence. No external services or databases were used.

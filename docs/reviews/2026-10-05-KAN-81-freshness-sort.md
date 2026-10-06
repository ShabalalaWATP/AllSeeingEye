# KAN-81 freshness sorting, 5 October 2026

The store now supplies its previous publication list as an optional freshness
hint. The helper resolves current keyed objects, checks distinct IDs, finite
current times and strict comparator order, then merges sorted new IDs with the
retained ordered records. Missing previous IDs are ordinary removals.

The publication list is not assumed to have eviction order. Any unsafe hint,
including malformed keyed entries, stale ordering or comparator ties, falls
back to the original full sort of the untouched Object.values sequence. No
persistent classification/index cache was introduced. Quotas, geographic
fairness, selected-event exceptions and downstream publication order remain
unchanged.

Baseline regression checks passed 27 tests and failed the two intended sort
budgets (5,250 over 250 and 5,150 over 200). The final candidate passed 217 tests
across 24 files. Scoped ESLint/Prettier, both TypeScript checks, production build,
bundle budgets and git diff checks passed. Independent source quality and
security reviews are clear. Initial non-null assertion lint failures were
repaired with explicit undefined handling; the retained repair was reviewed.

Final gzip bundle sizes were 202,540 bytes initial (245,760 limit) and 806,854
bytes globe (870,400 limit). These checks establish correctness and bounded
sorting work, not an application latency improvement. No new coverage run was
performed for these six files; previous rendering-milestone coverage does not
include them.

## Canonical observation

The unchanged original benchmark ran once per arm with pinned Node 24.19.0.
Both tests passed, all 40 candidate source pins, 13 shared inputs, 45 direct
packages per arm, runtime/metadata/prior-evidence pins matched before and after,
and owned jobs/handles closed without errors.

| Scenario | Baseline median/max ms | Candidate median/max ms |
|---|---:|---:|
| New IDs | 50.55 / 65.44 | 43.06 / 63.78 |
| Existing IDs | 31.86 / 40.83 | 28.12 / 32.83 |
| Mixed | 36.57 / 50.84 | 41.31 / 51.30 |
| Controls | 28.62 / 40.89 | 29.26 / 47.15 |

All candidate medians exceed 20 ms; new/mixed maxima exceed the strictly-under-
50-ms limit. Mixed/control observations were worse. No rerun or changed target.
The fixed-order developer-host pair does not establish causal attribution,
repeatability or equal cache histories. It does not exercise browser transport.
The private canonical-priority-pair-881-v4 packet preserves all raw evidence,
including earlier negative measurements. KAN-81 remains open.

## Earlier milestone release

PR 129 merged as bdd61712. Main CI 37347485689 and Deploy VPS 37349223233 passed,
including revision selection and the deployment verification job. Independent
public health/readiness checks returned ok/ready. This release contains the
previous rendering changes, not these six subsequent working files.

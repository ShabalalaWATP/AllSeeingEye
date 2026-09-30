# Combined notification CI repairs

Published source: `67de303932e731ccb3e1aa31d5fe7987c92e9666`.
[CI run 36703607838](https://github.com/ShabalalaWATP/AllSeeingEye/actions/runs/36703607838)
checks the combined forecast, source/export and notification tree. The statements
below record completed checks, not a claim that review, every job or release is
complete.

## Repairs and focused checks

- Three backend fixtures now reflect the additional lifecycle workers, explicit
  logging levels and webhook TLS/proxy configuration: 25 cases passed.
- The Atom import suppresses one XML-parser rule because this module only
  constructs and serialises XML. Three escaping/bounded-history cases, Ruff,
  formatting and Bandit passed; full CI Semgrep subsequently passed.
- Eight forecast watch behaviour cases cover loading, dates, paging, workspace
  access, cancellation and failures. Twelve focused cases passed, with all
  32 watch branches covered. The repair was published to PR #94 first.
- Eight source/export cases cover map/report downloads and LEI lifecycle
  boundaries. Twenty-three focused cases passed and exercised 22 previously
  uncovered branches. The repair was published to PR #95 first.
- Notification controls use the existing readable border token. Twenty-four
  meaningful behaviour cases cover account settings, permission, lifecycle,
  scoped alerts and errors. Ninety-one notification and surrounding cases passed,
  including the contrast regression; 31 previously uncovered branches were
  exercised. TypeScript and changed-file lint/format passed.
- Independent review found no actionable access, cancellation, cleanup or test
  validity issue. Nine repair commits passed Gitleaks with no leaks.

## Fresh combined coverage

The frontend merger passed its original thresholds, reviewed auth floors,
92% global branches and 70% branches for files containing at least 20 branches.
Artifact `frontend-coverage`, ID `11090229607`, reports:

| Metric | Covered / total | Displayed percentage |
| --- | ---: | ---: |
| Lines | 20,555 / 21,137 | 97.24% |
| Statements | 23,073 / 24,006 | 96.11% |
| Functions | 7,555 / 8,015 | 94.26% |
| Branches | 20,697 / 22,470 | 92.10% |

Independent LCOV summation matches the JSON branch counts exactly. The preceding
combined run covered 20,616 branches from the same 22,470 total, or 91.75%.
The new combined report covers 81 additional branches; this includes effects
beyond the 74 newly exercised branch keys identified by the focused selections.
No qualifying file falls below 70%. Forecast watches cover 32/32 branches,
email settings 31/32, push settings 22/26, map export UI 8/8, report export UI
49/52 and LEI lookup 20/20.

Downloaded LCOV SHA-256:
`ccd78e6845c6d82d632595dafb234cd85ee814a3ba4eceb5a58845def906fb06`.
Raw JSON and LCOV remain outside Git in the parent worktree directory
`pr96-repaired-ci-coverage`. The immutable run and artifact identify provenance.

Backend quality, its combined coverage/security-floor merger, frontend static
checks and full Semgrep passed at this checkpoint. PostgreSQL jobs were still
running when these coverage figures were recorded. No coverage floor was reduced,
no production data was touched and no live notification was sent. Review,
operator transport acceptance and explicit release approval remain separate.

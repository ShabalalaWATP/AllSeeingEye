# KAN-133: exact provider matching in KEV tests

PR #95 CodeQL alerts 5039 and 5040 identified URL substring matching in two
synthetic HTTP response selectors. These selectors use `AsyncMock`; they do not
perform network requests or enforce the application's destination policy.

The enrichment deadline test now selects FIRST responses by the parsed exact
`api.first.org` hostname and checks that the stalled request targets
`services.nvd.nist.gov`. The CISA preservation test matches the complete configured
catalogue URL and checks that the stalled enrichment request targets
`api.first.org`. The existing deadline, partial-score, request-count and CISA
preservation assertions remain unchanged.

No production code, scanner rules, suppressions or quality gates changed.

Local validation used this worktree's private Python environment after clearing
inherited application, database, PostgreSQL and environment-selection variables:

- `pytest tests/test_kev_scores.py tests/test_cyber_kev_collection.py --no-cov -q`:
  16 passed in 0.76 seconds.
- Ruff lint and formatting checks passed for both changed test files.
- Independent read-only review found no actionable issue. Unexpected-host
  assertions propagate rather than being swallowed by optional enrichment.

This record covers the local repair. Exact-head CodeQL and full CI results are
tracked on PR #95 before release.

# Alert and tracker selection fixes

Delivery record for [KAN-146](https://alex-orr.atlassian.net/browse/KAN-146),
[KAN-148](https://alex-orr.atlassian.net/browse/KAN-148) and
[KAN-147](https://alex-orr.atlassian.net/browse/KAN-147).

## Complete warning counts (KAN-146)

The evaluator previously limited candidates to 2,000 before checking keywords and
severity. An older retained match could disappear, and supported thresholds above
2,000 could never fire in a single scope. Sixteen regression cases reproduced the
defect across global, country, bounding-box and exact-area rules.

Internal `EventQuery(limit=None)` now selects every matching retained event without
ranking or pagination. It rejects offsets and geographic sampling. Public event
endpoints retain their existing bounded integer limits.

Every warning scope uses one admitted immutable snapshot when the store supports
cooperative reads. Country unions are evaluated once on that snapshot. Evaluation
counts all matches, records every matching country and retains only the newest 20
events as evidence, ordered by publication time and event ID. Retention remains the
store's existing memory budget; this does not recover already evicted events.

The independent security review found that a full public read queue could abort a
warning cycle. A cycle now shares a budget of two one-second admission backoffs.
If saturation persists, the affected rule is logged as deferred, remaining rules
are considered and old alerts are still pruned. Deferred rules are reconsidered in
the next cycle; this provides bounded recovery, not guaranteed alert latency under
sustained overload. Cancellation continues to propagate. Four real-store queue
regressions failed before the repair and passed afterwards.

## Closed warning windows (KAN-148)

Warnings use the closed publication interval `[now - window, now]`. Unknown or
timezone-naive publication dates are excluded. The store's general half-open time
contract stays unchanged: warning selection uses the next representable instant
after `now` as its exclusive upper bound. At the largest representable clock value,
there is no later instant to exclude. Domain evaluation independently checks both
bounds. Future scheduling metadata such as launch NET does not change publication
eligibility.

Thirteen regression failures reproduced future-date admission and naive-date
comparison errors. After the fix, the 90 selected warning and admission tests
passed, including exact endpoints, adjacent microseconds and exact-area selection.

## Independent tracker components (KAN-147)

`EventQuery.subtypes` filters before ranking, alongside the existing source filter.
Maritime warnings, launches, Kp readings, NOAA bulletins and each cyber component
now select their own relevant records before their 5,000-event cap. Fresh AIS or
unrelated satellite/cyber records cannot displace those records. The station list
uses the CelesTrak stations source, matching the UI's crewed-stations scope.

Board totals and tallies describe the newest **up to 5,000 matching retained
records per component**, not complete provider totals. Latest/notable lists retain
their existing smaller limits. Launch publication recency and NET scheduling
remain distinct; this change preserves the existing seven-day publication window
and the allowance for launches scheduled in the preceding day. The maritime
report background uses the corrected board selection.

Five saturation, station-scope and report-background regressions reproduced the
defect. Eight new guard/regression tests and 19 existing module/feed tests passed.
Two cap tests explicitly preserve the newest 5,000 matching-record semantics.

## Validation and delivery

- Full backend run on Windows, Python 3.13.3, six workers: **9,817 passed, 93 skipped,
  one failed**, in 820 seconds. Coverage was **93.78%**, passing the unchanged 90%
  gate. The suite itself did not pass because of the failure described below.
- All added warning, query, queue and module regressions passed. Focused runs also
  covered existing warning routes, exact areas, cooperative cancellation, module
  APIs, report background and feed normalisation.
- Ruff lint/format, mypy, import boundaries, Bandit, Gitleaks and file-length checks
  passed. OpenAPI export left the committed schema unchanged. No HTTP API, database
  migration, dependency or CI configuration changed.
- Independent code, security and documentation reviews completed. The admission
  finding and two documentation wording corrections were addressed; no remaining
  blocking implementation finding was reported.

The one local failure is
`test_research_import_worker.py::test_remote_parser_unavailable_fails_closed`:
`vars(asyncio)["open_unix_connection"]` raises `KeyError` on Windows. The test and
research-import adapter files are unchanged from base commit `9a01161a`; the same
lookup is present in that base. This existing platform limitation is already tracked
as [KAN-29](https://alex-orr.atlassian.net/browse/KAN-29), outside these alert/board
tickets. No test was skipped or threshold lowered to hide it. Linux
SQLite/PostgreSQL and frontend CI results remain separate gates, tracked in PR #81.

The three related fixes and the admission follow-up share a query boundary and are
separate commits in [draft PR #81](https://github.com/ShabalalaWATP/AllSeeingEye/pull/81).
Production release requires review and Alex's approval.

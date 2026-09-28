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

## Validation and delivery

The initial 16 regression cases failed before the change. With the fix, all 54
selected warning, exact-area and cooperative-reader tests passed. A further focused
run passed 38 tests covering the volume cases, query contract, country metadata,
synchronous fallback, worker snapshots and cancellation admission. Ruff, mypy,
import boundaries and Bandit passed. An independent code review found no blocking
issue. Full-suite validation and final reviews are pending the remaining fixes.

The three related fixes share a query boundary and will be separate commits in
one draft PR. Production release requires review and Alex's approval.

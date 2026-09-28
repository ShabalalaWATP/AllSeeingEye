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

## Validation and delivery

The initial 16 regression cases failed before the change. With the fix, all 54
selected warning, exact-area and cooperative-reader tests passed. A further focused
run passed 38 tests covering the volume cases, query contract, country metadata,
synchronous fallback, worker snapshots and cancellation admission. Ruff, mypy,
import boundaries and Bandit passed. An independent code review found no blocking
issue. Full-suite validation and final reviews are pending the remaining fixes.

The three related fixes share a query boundary and will be separate commits in
one draft PR. Production release requires review and Alex's approval.

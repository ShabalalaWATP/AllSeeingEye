# ADR 0003: Live event store is an in-memory bounded cache

Status: Accepted (proposed 2 September 2026, accepted by Alex 3 September 2026)

## Context

The app ingests thousands of items per hour from dozens of feeds. Alex has asked that the product never grow a large database on a home machine; only AI reports (and by implication their evidence) should be saved. The globe still needs a rolling window of recent events to be useful, and the pipeline needs recent items to detect corroboration and bursts.

## Options

1. **In-memory store with per-category budgets** (retention window, item cap, global memory budget), pruned every minute, optionally snapshotted to a cache file so restarts are not blank. Exposed through an `EventStore` port.
2. **Redis** with `maxmemory` and TTLs. Bounded by construction and shareable across processes, but adds a service and offers only rudimentary spatial queries.
3. **PostgreSQL unlogged tables with a TTL sweeper.** SQL and PostGIS for free, but heavy write churn, table bloat, vacuum load and a disk footprint that is exactly what Alex wants to avoid.

## Decision

Option 1, behind a port so that option 2 can replace it if the collectors ever move to a separate process. Historical questions are answered by querying upstream APIs on demand with a short cache. Long-term "normal levels" for warning rules are kept as small hourly aggregates in PostgreSQL, never as raw events.

## Consequences

- A single API process for now; scaling out requires the Redis adapter.
- The admin System page must show live store occupancy against budgets; an alert fires at 80 percent.
- Evidence a report cites is copied into durable storage at generation time (evidence freezing), which is the only way live data becomes permanent.

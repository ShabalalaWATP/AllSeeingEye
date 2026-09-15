# ADR 0017: Durable subscription editions and retained history

Status: accepted for the local single-process implementation, 14 September 2026. PostgreSQL and multi-process operation still require separate acceptance.

## Context

A recurring question must produce traceable reports without running the source/model pipeline synchronously in the scheduler. Calendar updates need a stable intended slot across daylight-saving changes and restarts. An interrupted paid call cannot safely be retried when its outcome is unknown. Users also need to stop future runs without losing earlier edition and report history.

## Decision

- Each accepted due slot creates one immutable edition and one durable report job in a transaction. A unique due-slot identity prevents a second admission of that slot. The browser does not need to remain open.
- The saved definition includes an IANA timezone and local wall-clock rule. Due-slot identity and evidence windows use the intended UTC due instant. Catch-up coalesces missed slots under a bounded policy instead of issuing a burst of paid reports after an outage.
- Model and source calls use persisted reservations and receipts. Known completed work is reused after restart. An uncertain paid outcome remains paused with its reservation retained; it is not replayed merely because a worker lease expired. Late workers cannot publish through an expired lease.
- A schedule pause fences new admission and pauses its active job at a safe checkpoint. Resume preserves the definition and edition history. `DELETE /api/schedules/{id}` archives through a tombstone, cancels future work and retains editions, selected index entries and reports. The API list excludes archived schedules, while previously authorised report records remain available.
- Report comparison uses exact frozen editions. Inadequate coverage, ambiguous claim mapping and source outage must not become an unqualified change or no-change claim.

## Consequences and limits

The operating topology remains one API process with local fair batching. The database carries additional edition, index, reservation and tombstone state, so backups and forward-compatible migrations matter. A rollback must stop new dispatch without dropping retained history or reviving the old synchronous producer for an admitted slot. In-app events are available, but notification policy and external delivery remain future work. Populated PostgreSQL upgrade, multi-process scheduling and live provider recovery are not accepted by the local SQLite tests.

See [Subscription operations](../SUBSCRIPTIONS_OPERATIONS.md) and the [acceptance record](../plans/research-subscriptions/ACCEPTANCE.md) for current checks and remaining gates.

# Live-map recovery after incomplete updates

The browser keeps a bounded mirror of the shared live store. Incremental updates
are not an archive or replay log. When the server cannot provide a complete set
of removals, the browser must discard its stale mirror and reload a snapshot.

## Protocol

Authenticated `/api/stream` can emit:

```text
event: event.resync
data: {"reason":"expiry_overflow"}
```

The other permitted reason is `stream_gap`. Unknown reasons are ignored by both
the server serializer and browser handler. These resynchronisations are independent
of category filters (bulk refresh hints, below, are not) and follow the same current-session revalidation as every
other stream message. A revoked session receives `bye`, not recovery data.

`expiry_overflow` means expiry bookkeeping exceeded its 10,000-ID notification
budget. The store still removes every expired/evicted record. It bounds pending
eviction IDs, remembers overflow until the next prune, and asks for a snapshot
instead of publishing an incomplete list. Reinsertion removes an earlier pending
tombstone, and final removal lists exclude IDs currently retained by the store.

`stream_gap` means a slow subscriber lost a live-event message because its queue
filled. The recovery signal lives outside that queue so it cannot itself be
dropped. Before the barrier is returned, queued old upserts, expiries and resyncs
are discarded; retained non-event messages keep their order. This also applies
when the consumer was already waiting before the producer burst. Later event
deltas follow the barrier and can safely reconcile with the replacement snapshot.
Dropped alert/health delivery is not made durable by this mechanism.

## Browser behaviour

The handler invalidates an in-flight request, clears events, selection, statistics
and snapshot-coverage flags, then loads a replacement snapshot. Display filters
remain selected. Changes arriving during that load use the existing bounded
upsert/tombstone reconciliation journal. Late cancelled responses and logout
cannot restore an old mirror. If reload fails, stale data stays cleared and the
normal loading error is displayed.

The replacement remains subject to the 2,000-event snapshot and 5,000-event browser
limits, with existing coverage disclosures. This recovers an accurate bounded
view; it does not promise every retained server record is visible. Repeated new
gaps can require another reload. Persistent overload still needs operational
capacity work and is not solved by unbounded queues or snapshots.

## Verification

Regression cases cover 10,001 expirations, bounded immediate-eviction bookkeeping,
reinsertion before prune, scheduler publication, subscriber overflow and waiting
consumer ordering. Browser tests cover preservation of filters, new stream
deltas, late cancelled responses, reload failure, logout and delivery through a
mounted globe. Session-revocation tests include resync frames. Browser rendering
uses the existing mocked map engine; this is not GPU visual acceptance.

## Bulk feed updates

A single upsert of more than 500 events or about 384 KiB, such as an AIS or ADS-B
batch, is not streamed record by record. The bus replaces it with a soft refresh
hint that names the partitions the batch touched:

```text
event: event.resync
data: {"reason":"snapshot_required","categories":["maritime"],"source_id":"aisstream"}
```

The categories cover every published event in the batch, including neighbouring
records whose grade moved during contextual regrading. Each stream narrows the list
to its own category filter, and a stream filtered only to unrelated categories does
not receive the hint. An empty filter still means every category. A batch with any
unrecognised content produces a hint without `categories`, which every stream
receives. A hint after an unresumable reconnect also carries no categories.

The browser keeps its mirror visible and coalesces hints for at least ten seconds
after its previous snapshot started. It then refreshes only the named partitions:
one category-scoped snapshot request, statistics, and only the coverage supplements
for those categories (for maritime, the extra maritime and reported military
vessel requests, not aviation, satellite or FIRMS requests). The response replaces
the whole partition, so records that expired or no longer match are removed, while
other categories keep their records and object identity and their map layers keep
their rows. Stream deltas received during the request are journalled and win over
the response; a viewport change, stream gap or reconnect supersedes the request.
The existing 2,000-event snapshot limit, 5,000-event browser limit and source
reservations still apply.

Missing or unknown categories, or a mirror that has not completed a full snapshot,
fall back to a full reload. `stream_gap`, `expiry_overflow` and access changes keep
the clear-and-reload behaviour described above. A failed or rate-limited soft
refresh keeps the last valid mirror and retries after 10, 20 and 40 seconds, then
reports that the refresh failed until the next hint or a manual reload.

Identical concurrent `GET /api/events` reads share one selection and response
build while the retained store is unchanged. Results are keyed by the normalised
query and a store generation that advances on every insert, replacement, expiry,
eviction and regrade, and at most four results are kept for two seconds. Every
caller is still authenticated, recorded as a map interest and checked by its
release fence, and one account keeps its existing limit of two concurrent reads.
`scripts/benchmark_event_reads.py` compares direct and shared reads offline.

## Resuming after a reconnect

Every stream frame carries an SSE `id` of the form `<epoch>-<sequence>`. The epoch
is 12 random hexadecimal characters chosen when the API process starts, and the
sequence increases with every bus message. When a stream skips messages because of
its category filter, it still advances its position, sending an id-only frame at
most once per 15-second ping.

The browser reconnects with a `Last-Event-ID` header, for example after its access
token renews every 15 minutes. The server keeps a bounded replay window of recent
public messages: at most 1,000 messages, 120 seconds and about 8 MiB of estimated
payload, holding upserts, expiries, resyncs and source health only. If the id
belongs to this process and is still inside the window, the server re-applies the
session check, replays the missed public messages through that client's category
filter and sends `hello` with `resumed: true`; the browser keeps its mirror. Any
other id (another process, a future or malformed id, or one older than the window)
gets `hello` with `resumed: false` followed by `event.resync` with
`snapshot_required`, and the browser reloads its snapshot once.

Alerts are never replayed, because they are authorised per user at delivery; an
alert published while a browser is disconnected is not re-sent, as before. A tab
that was hidden still takes a fresh snapshot when it becomes visible. Public
messages are encoded once per category filter and the same text is shared by
every open stream. A connection that receives nothing, not even a ping, for 45
seconds is abandoned and reconnected, and reconnection delays use full jitter
within the existing 1 to 30 second backoff.


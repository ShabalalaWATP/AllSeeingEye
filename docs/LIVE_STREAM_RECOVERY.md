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
the server serializer and browser handler. Resynchronisation is independent of
category filters and follows the same current-session revalidation as every
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


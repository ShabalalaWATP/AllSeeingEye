# ADR 0022: Disposable live-store snapshot across restarts

Status: accepted, 26 September 2026. Approved by the operator as a narrow exception
to the rule in [ADR 0008](0008-bounded-report-search.md), [ADR 0010](0010-teams-and-access.md)
and the project guidance that raw live events are never persisted. It realises the
optional cache file anticipated by [ADR 0003](0003-live-event-store.md). Events still
never enter the database.

## Context

The live store is a bounded in-memory cache. Every restart, deployment or crash
started it empty. Fast feeds refill within minutes, but news keeps 72 hours and
conflict, cyber and humanitarian categories keep up to 30 days. Many upstream feeds
return only their newest items, so a restart lost history that no later poll could
recover until it aged out naturally. The satellite cache (`docs/SATELLITE_COVERAGE.md`)
already showed that one bounded, replace-in-place file can fix a restart problem
without becoming an archive.

## Decision

Keep one compressed snapshot file of the shared live store, and nothing else.

- **Location.** `ASE_LIVE_SNAPSHOT_PATH`, default `data/live-store.jsonl.gz`, relative
  to the API working directory like the SQLite database and satellite cache. An empty
  value disables the snapshot. Under `ASE_ENV=test` the default is empty, so tests only
  use a snapshot when they opt in.
- **Format.** Gzip of UTF-8 JSON lines: a header (`format` `ase-live-store`,
  `version` 1, `saved_at`), one record per event holding exactly the public `Event`
  fields, then a trailer with the event count. Format changes bump the version.
- **Saving.** Every `ASE_LIVE_SNAPSHOT_INTERVAL_SECONDS` (default 300, 60 to 3,600)
  and once on graceful shutdown, after every feed and background worker has stopped.
  A lock stops saves overlapping. Event references are captured on the event loop;
  encoding and compression run in a worker thread. The file is written to a temporary
  sibling created exclusively (owner-only on POSIX), flushed with `fsync`, then
  renamed over the previous file with `os.replace`. The directory is synced on POSIX.
- **Bounds.** `ASE_LIVE_SNAPSHOT_MAX_MB` (default 128, 1 to 1,024) caps the compressed
  file. The decompressed content is capped at `ASE_LIVE_STORE_MEMORY_MB`, and a file
  holds at most the sum of the per-category item caps (313,000 events today), newest
  first. Exceeding a cap skips the save with a log line and leaves the previous file;
  nothing is truncated. Events that cannot be encoded are skipped individually.
- **Loading.** Once during startup, before any feed worker starts, and only into an
  empty store. Symbolic links (checked before opening, with `O_NOFOLLOW` where the
  platform has it), non-regular files, oversized input, lines over 8 MiB, an unknown
  format or version, a missing or wrong trailer, trailing data, a failed gzip checksum
  and undecodable JSON all cause the whole file to be ignored with a log line. Records
  with unknown fields or invalid values are skipped one by one. Startup never fails
  because of the snapshot. Temporary siblings left by a crash are removed.
- **Retention.** Restored events pass through the store's normal prune: retention
  windows, vessel and satellite position freshness, per-category caps and the memory
  budget. An event past its window is dropped on load, not shown again.
- **Readers.** Restored events keep their id, content hash, grade, story and
  provenance, so the store API returns them exactly as it did before the restart. A
  later poll upserts over them normally: unchanged when identical, updated otherwise.
  No stream messages are sent for them because no client is connected during startup.
- **Interrupted startup.** The final save runs only after a completed load, so a
  cancelled startup cannot replace a good file with a partial store. Partial-startup
  unwinding in `ase.app_lifecycle` still stops every worker it started.

The snapshot holds only what the shared store holds: public observations that any
signed-in user can already read through the event API. Alerts, sessions, accounts,
credentials, reports, private research inputs and per-job report stores are never in
it. It is not a database table, an archive, a search index or a backup.

## Consequences

- Restarts keep news and conflict history, less the downtime, instead of starting
  empty. A crash loses at most one interval of changes.
- Disk use is one capped file plus, during a save, one temporary sibling.
- A restart no longer clears a stale or withdrawn event; it remains until it expires
  or a poll replaces it. Deleting the file while the API is stopped gives an empty
  start.
- Startup decodes and restores the file before the API accepts requests, and shutdown
  includes one final save. A stop timeout shorter than that save leaves the previous
  file in place. Restore and save times for a full production-sized store have not
  been measured.
- One API process per file, consistent with the supported topology. Two processes
  sharing a path would each replace the file, never corrupt it.
- The snapshot is disposable and deliberately excluded from backups
  (`docs/BACKUP_RESTORE.md`). Anyone with host access to the data directory can read
  it, as with the database; it contains public data only.

Tests cover the round trip of every event field, retention on load, damaged,
truncated, foreign, oversized and wrong-version files, skipped invalid records,
symbolic-link refusal, atomic replacement on failure, both size caps, the disabled
setting and the startup and shutdown order. These are software tests, not
measurements of production restart times.

# Public satellite coverage

The satellite adapter expands the former stations-only feed to four independently monitored CelesTrak sources. The active catalogue uses CSV, which supports catalogue IDs above 99,999 and stays within the existing 5 MiB HTTP response bound. No new package or credential is required.

| Source ID | Published selection | Bound |
| --- | --- | --- |
| `celestrak_stations` | Stations and associated vehicles | 20,000 rows |
| `celestrak_active` | Active satellites, including large commercial constellations | 20,000 rows |
| `celestrak_military` | CelesTrak's public military group | 20,000 rows |
| `celestrak_skynet` | Publicly named Skynet objects, excluding rocket bodies and debris | 20,000 rows |

A public probe on 8 September 2026 returned 16,510 rows from the active CSV (2,495,875 bytes), a populated military catalogue and 13 Skynet name matches. One Skynet match was launch hardware, which the adapter excludes. These are retrieval observations, not a guarantee of future catalogue size or successful propagation for every row. Skynet matches include historical spacecraft; presence in this catalogue does not establish current operational service. The app does not manufacture an orbit for a satellite absent from the public catalogue.

## Position meaning and freshness

Positions are SGP4 predictions from public mean orbital elements. They are not live sensor observations. The existing spherical Earth subpoint conversion is retained, so latitude and altitude are approximate; this is a general visualisation rather than a precision orbit determination or pass-planning tool.

Each event includes NORAD ID, original element epoch, prediction time, epoch age in hours, catalogue group and an explicit `position_kind=propagated`. Elements older than three days are marked stale. Elements older than fourteen days, more than one day in the future, invalid records and propagation failures do not produce positions. Element downloads are cached for two hours and positions are recalculated on each two-minute poll. A failed refresh retains previously usable elements and reports degraded source
health while computing clearly labelled new predictions from those same elements.
It preserves the original element epoch and download timestamp. It never treats
an error response as new orbital data.

A `military_public_catalogue` flag means the source published the object in its military group or the object has a Skynet family name. `affiliation_basis` records that distinction. This is not a comprehensive classification of military, commercial or dual-use assets. It does not infer operational tasking or the position of undisclosed spacecraft. Different source groups overlap; map rendering should deduplicate by `norad_id`, preferring the specific military or Skynet record.

## Verification and sources

Deterministic tests cover six-digit catalogue IDs, more than the former 500 objects, the 20,000-row bound, duplicate IDs, malformed and stale orbital data, cache refresh, source labels and exclusion of Skynet launch hardware. Network calls are excluded from tests.

- [CelesTrak public element groups](https://celestrak.org/NORAD/elements/)
- [CelesTrak GP formats and query parameters](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
- [MOD description of the Skynet capability](https://www.gov.uk/guidance/skynet-6)
- [OSIRIS satellite route](https://github.com/simplifaisoul/osiris/blob/master/src/app/api/satellites/route.ts), inspected revision `fac8d1b1dd3f9aab87bdeccdd04f05c25d5a3bb8`. OSIRIS also starts from the active catalogue and adds overlapping groups; this implementation uses bounded CSV/JSON rather than legacy five-digit TLEs.

## Browser loading and controls

The browser retains its 5,000-event global bound. It reserves up to 1,500 places for ships, 1,500 for satellite positions and 1,000 for FIRMS thermal detections, leaving at least 1,000 places for other events when all reservations are full. Unused reservations remain available to other events. Alongside the ordinary snapshot it requests a space supplement (up to 1,500), then a separate combined stations/military/Skynet supplement (up to 1,500). A separate 1,000-record request covers both keyed and public NOAA-20 FIRMS source IDs when disaster records exist. Source-specific priority keeps these smaller satellite catalogues visible when a commercial constellation fills the broader active catalogue. These limits mean the map is a bounded view of the full server catalogue, not a promise to render every tracked satellite simultaneously.

The satellite panel offers all, stations/crewed vehicles, public military and Skynet selections. Counts describe loaded distinct objects. Rendering collapses overlapping feeds by NORAD ID and favours Skynet, military, then stations records; other map categories pass through unchanged. The event inspector retains original source attribution and orbital-age attributes. Failed supplements show an error while retaining a successful primary snapshot. Existing live-update reconciliation, session cancellation and tombstone handling remain in force.

Supplemental requests run one at a time. The event API permits two queued or
active reads per user, so a snapshot leaves capacity for another panel instead
of exhausting that allowance before the smaller satellite catalogues load.
These requests read retained server data; they do not download orbital elements
again. A failed supplement does not prevent later catalogues from loading.
Cancellation stops queued requests and prevents late results from replacing a
newer snapshot or restoring a signed-out session.


## Final runtime and freshness checks

The final authenticated runtime probe returned 22 station/crewed objects,
24 public military catalogue objects and 12 Skynet objects. The active catalogue
was returning HTTP 403 at that point. The earlier 16,510-record result was a
successful provider retrieval, not a claim that those objects remain available
in the running application. Failed network retrievals wait two hours before the
next upstream attempt, including when no elements were cached.

Position snapshots expire after ten minutes, separately from the two-hour
orbital-element cache and fourteen-day maximum element age. The server prunes
expired positions on its existing maintenance cadence; the browser hides expired
predictions on its thirty-second clock even if the live connection is lost.
Precision labels explicitly identify propagated orbital estimates. These rules
avoid presenting a seven-day retained SPACE event as a current satellite position.


## 8 September 2026: restart and provider-limit repair

CelesTrak's current GP documentation enforces one download per update for the
active catalogue. A guarded live probe returned HTTP 403 with the documented
unchanged-data response, confirming that this was a duplicate-download refusal.
The earlier successful download had been held only in memory and lost on restart.
CSV/JSON already support the expanded catalogue IDs; reverting to TLE would not
resolve the fault.

The application now stores the latest orbital inputs and next permitted request
in `ASE_SATELLITE_CACHE_DIR` (default `data/celestrak`, relative to the API working
directory). Downloads reserve the two-hour interval before network I/O. Restarts,
manual tests and interrupted downloads preserve that reservation. Parsing and
atomic disk replacement run outside the event loop. Cancellation waits for an
outstanding write; shutdown also awaits retiring source tasks.

The cache contains four fixed source files, each at most 12 MiB and 20,000 rows.
Only named orbital fields and scalar values are retained. Temporary replacement
files add at most one further bounded file per writing source. Wrong-source,
oversized or damaged files cause a conservative two-hour wait, with a diagnostic.
The cache is local, ignored by git, outside the database and outside the web root.
It is not an event archive. Use one feed worker per directory, consistent with
the application's supported topology; it is not an interprocess request broker.

The documented unchanged-data 403 reuses a warm cache, or waits two hours when
there is no local copy. Other 403/404 responses pause downloads across restarts.
An administrator can use **Administration → Sources → Reset** after reviewing
the provider response. Reset still respects the minimum two-hour interval.
Transient failures use the same bounded cooldown. Cache-backed predictions can
continue during a pause until their underlying elements exceed fourteen days;
source health remains degraded for a real refresh failure. Waiting polls do not
accumulate fictitious upstream failures or trip the circuit breaker.

Each prediction exposes `elements_downloaded_at` and `element_refresh_failed` in
addition to its orbital epoch and prediction time. Prediction time is included
in its change hash, so nearly stationary geostationary satellites keep fresh
position timestamps rather than disappearing after ten minutes. A malformed
replacement catalogue cannot erase a usable warm cache.

The active catalogue needs the next permitted provider update before the initial
empty cache can be populated. No satellite positions were fabricated or imported
from a historical download and presented as current. Runtime status below will
record the observed outcome independently of deterministic test results.


Runtime verification at 15:28 UTC on 8 September: frontend 5174, API health and
mock-user login returned HTTP 200. Authenticated snapshots held 22 station
objects, 24 public military catalogue objects and 12 Skynet objects, with download
provenance. Fresh connector instances reproduced those counts directly from disk
while a test transport rejected every possible network call. The active cache
remains empty with its next permitted attempt at 17:16 UTC (18:16 UK time).
This is a scheduled retry time, not a guarantee of provider availability.

Verification: 184 distinct backend regression tests passed, including source
admission, administrator reset, credential redaction, HTTP bounds and scheduler
behaviour. Satellite-module coverage is 98.37%, including branches. Ruff,
formatting, strict mypy and both architecture contracts passed. No frontend code,
provider credentials, database schema or dependency versions changed. Browser
visual verification and successful live active-catalogue population remain
unclaimed.


## 9 September: worldwide map retrieval

The [worldwide coverage update](WORLDWIDE_COVERAGE.md) supersedes earlier browser
loading details: geographic sampling occurs before API limits, viewport requests
fetch relevant retained records, and all supplements share that scope. Browser
capacity remains 5,000. Provider reception, sampling and source freshness limits
still apply. See the update for collection changes and measured validation.

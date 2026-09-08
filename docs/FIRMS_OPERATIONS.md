# NASA FIRMS thermal observations

The default public connector downloads NASA's published NOAA-20 VIIRS 24-hour CSV
without a key (`firms_public_noaa20`). It uses the fixed official URL published in
NASA's [Active Fire Data catalogue](https://firms.modaps.eosdis.nasa.gov/active_fire/).
It validates at most 10 MiB and 100,000 rows atomically, polls every 30 minutes,
and preserves acquisition timestamps separately from download time. The existing
bounded event store and map filters limit what is displayed. This is a published
snapshot, not a live sensor stream or a guarantee of complete current coverage.

The optional keyed connector uses NASA's NOAA-20 VIIRS Area API. It supplies
`firms_viirs_noaa20` events to the existing scheduler, source controls, health
registry and bounded live store. Both dashboard projections recognise the
`thermal_detection` subtype, draw a sensor symbol and honour the FIRMS switch.
The switch changes display only. No MAP_KEY is bundled. Public and Area API
observations have separate source IDs; overlapping observations are the same
NASA sensor evidence and must not be counted as independent corroboration.

## Administrator setup

1. Request a free MAP_KEY through the [official NASA Area API page](https://firms.modaps.eosdis.nasa.gov/api/area/).
   NASA sends it to the supplied email address. The administration panel links
   directly to this workflow; the map switch alone does not configure collection.
2. Configure `ASE_ENCRYPTION_KEY` on the server and retain it separately for
   recovery. Database credentials use the same Fernet boundary as model secrets.
3. Open Administration > Sources > FIRMS connection. Save a draft key, test that
   exact draft, then confirm the successful connection. Keys are never read back.
   A draft and its successful test proof are valid for 15 minutes. Editing or
   retesting invalidates old proof; activation is tied to the current administrator
   session. Testing fetches a bounded sample without saving or publishing records.
4. Confirmed database credentials take effect on the next poll without restarting
   the backend. Source enable/disable remains separate. In-flight results and
   failure health updates are discarded if the active credential generation or
   source admission changed before publication.
5. Removing the connection clears the database active and draft key. It does not
   erase existing observations or their frozen report copies.

Run the normal database migration procedure through migration 0032 before using
this release. The migration follows inventory migration 0031. Downgrade refuses
while retained FIRMS configuration exists; do not delete operator configuration
simply to force a downgrade.

`ASE_FIRMS_MAP_KEY` remains supported and takes precedence over database keys.
When present, the panel displays an environment-managed connection and refuses
key mutation. It never copies the environment key into the database or silently
replaces it. Environment changes still require the deployment's normal restart.

`ASE_FIRMS_AREA` remains server configuration: `world` or
`west,south,east,north`, for example `20,40,60,70`. Dateline-wrapping boxes are
rejected; multiple-region collection is not implemented. The configured area is
bound to a draft's test validity. Adding `firms_viirs_noaa20` to
`ASE_FEEDS_DISABLED` is an operator veto over testing, confirmation and polling.
The display filter changes rendering only, not collection authority.

## Local readiness check, 8 September 2026

The local backend configuration was inspected without printing credentials or
modifying the database. No environment MAP_KEY or encryption key was configured.
The SQLite database reported migration `0026`, and `firms_credentials` was absent.
Consequently this local instance cannot yet use the database-backed Area API
connection journey. Public download collection does not require those credentials.
For the optional keyed connection, the required operator steps are:

1. Back up the intended database and apply the normal migrations through `0032`
   (or the current head) using `uv run ase migrate` from the backend directory.
2. Configure and securely retain `ASE_ENCRYPTION_KEY`, then restart the backend.
3. Request the NASA MAP_KEY and complete the administrator test/confirm journey.
   Alternatively, an operator-managed `ASE_FIRMS_MAP_KEY` can supply collection
   credentials, with the normal migrations still required for application state.
4. Enable the source in Administration > Sources and enable FIRMS on the map.

The official Area API documentation was reachable and still lists the configured
`VIIRS_NOAA20_NRT` product and URL contract. No authenticated live request was
possible without a MAP_KEY. No migration, registration or secret creation was
performed during this check.

The new public adapter was exercised through the application's DNS-pinned HTTP
client against the official CSV: 62,025 observations passed validation. Acquisition
times ran from 7 September 2026 00:01 UTC to 8 September 2026 00:01 UTC. This
demonstrates real public data access and parser compatibility, not instantaneous
coverage. Downloaded long confidence labels (low, nominal, high) are normalised
to the same sensor codes used by the Area API. The fixed NOAA-20 product establishes
the VIIRS instrument when the public CSV omits that column.

Later in the same session, the operator supplied a development MAP_KEY and stored
it in the ignored backend environment. A real Area API fetch then returned 12,741
validated observations, with the newest acquisition at 8 September 2026 11:33 UTC.
The environment credential path now reads its status and releases polled data
without querying the optional `firms_credentials` table. It needs no encryption
key because it does not persist the environment secret. Existing authorisation,
source enable/disable checks and administrator locks remain in force. Database
credential management still requires the normal migrations and encryption setup.

Integration exposed a separate scaling fault: narrative headline clustering built
millions of candidate pairs for identical sensor labels, blocking local API health
requests and consuming approximately 2.4 GB of process memory. Instrument records
now receive individual provisional grades and story identities, without entering
narrative clustering or increasing a news item's contextual support. This also
prevents neighbouring thermal pixels from appearing to be separate reporting of
one claim. A deterministic 5,000-record regression checks that only narrative
records reach the clustering function. After the fix and local backend restart,
three health requests returned HTTP 200 in 0.474, 0.268 and 0.280 seconds.

## Collection bounds

One request every 15 minutes retrieves the latest UTC calendar day from
`VIIRS_NOAA20_NRT`, not a rolling 24-hour interval. Polling does not change the
satellite revisit time or guarantee immediate coverage. The connector accepts
at most 5 MiB and 30,000 CSV rows per poll, rejects malformed or oversized batches
atomically, and uses the existing scheduler timeout/backoff. If a world response
exceeds these limits, configure a regional box. A failed poll does not mean no
fires; previously admitted records remain subject to normal store retention.

The event records acquisition and retrieval separately. It retains the source's
low/nominal/high confidence code, processing version, Kelvin brightness,
kilometre scan/track dimensions and megawatt fire radiative power. Those are
sensor measurements, not probabilities of an intelligence claim. The point is
the nominal 375 m pixel centre; it does not define a fire perimeter. Cloud,
coverage and overpass timing limit observation. Thermal detections alone do not
establish cause, an attack or damage. Source reliability remains unassessed.
Repeated observations use stable IDs; changed sensor fields update their hash.

See NASA's [VIIRS attribute description](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html)
and [Area API example](https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html).
Acknowledge NASA LANCE/FIRMS when using its data.

## Credential protection and acceptance

The key-bearing URL is confined to a protected request object. It is absent from
public source metadata and events. Requests retain DNS pinning, size limits and
timeouts, forbid redirects and conditional URL caching, and return fixed errors.
Task-local filters suppress diagnostics from the locked HTTPX/HTTPcore emitting
loggers throughout the request and response-close lifecycle. Other concurrent
requests retain their logging. Recheck logger coverage when upgrading these
dependencies; custom HTTP instrumentation must preserve this boundary.

Tests use synthetic CSV and mocked HTTP responses. The public CSV live probe is
recorded above, together with the later authenticated Area API probe. GPU visual
acceptance remains unverified. Computer-use policy denied
the requested API registration workflow; no account, key or Gmail verification
was created. No alternate registration route was used.

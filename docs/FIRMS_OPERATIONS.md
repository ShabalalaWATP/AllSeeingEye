# NASA FIRMS thermal observations

The optional live connector uses NASA's NOAA-20 VIIRS Area API. It supplies
`firms_viirs_noaa20` events to the existing scheduler, source controls, health
registry and bounded live store. Both dashboard projections recognise the
`thermal_detection` subtype, draw a sensor symbol and honour the FIRMS switch.
The switch changes display only. No key or operational connection is bundled.

## Administrator setup

1. Obtain a MAP_KEY through the official NASA registration workflow. This editor
   does not create an account or perform registration.
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

## Bounds and interpretation

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

Tests use synthetic CSV and mocked HTTP responses. Real API compatibility,
coverage and GPU visual acceptance remain unverified. Computer-use policy denied
the requested API registration workflow; no account, key or Gmail verification
was created. No alternate registration route was used.

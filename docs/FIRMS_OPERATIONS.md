# NASA FIRMS thermal observations

The optional live connector uses NASA's NOAA-20 VIIRS Area API. It supplies
`firms_viirs_noaa20` events to the existing scheduler, source controls, health
registry and bounded live store. Both dashboard projections recognise the
`thermal_detection` subtype, draw a sensor symbol and honour the FIRMS switch.
The switch changes display only. No key or operational connection is bundled.

## Server setup

1. Obtain a free MAP_KEY from the [official NASA Area API page](https://firms.modaps.eosdis.nasa.gov/api/area/).
2. Set `ASE_FIRMS_MAP_KEY` in the deployment's private environment or secret store.
   Do not put the key in chat, browser code, screenshots or version control.
3. Optionally set `ASE_FIRMS_AREA` to `west,south,east,north`, for example
   `20,40,60,70`. The default is `world`. Dateline-wrapping boxes are rejected;
   multiple-region collection is not implemented in this connector.
4. Restart the backend and check the source in Administration. Existing source
   enable/disable and circuit-breaker reset controls apply. Adding its ID to
   `ASE_FEEDS_DISABLED` excludes it at startup.

This milestone uses server configuration. A dedicated administrator credential
editor and connection-test workflow for non-LLM sources remains future work.

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

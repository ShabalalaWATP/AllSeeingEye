# Map layers and planning tools

Updated 9 September 2026.

## Operator controls

- Space is one left-rail category. Its filter disclosure contains the existing
  satellite catalogue choices. There is no separate satellite-filter rail icon.
- Conflict reports have a crossed-swords symbol and filters for reported type,
  text, source and location precision. Historical monthly baselines remain opt-in.
  Counts describe loaded reports, not verified or independently unique incidents.
- Natural hazards have their own category disclosure with hazard type, acquisition
  or report time, explicit earthquake magnitude and GDACS impact-level filters.
  Unknown measurements can be retained; magnitudes are not inferred from another
  provider's severity scale. FIRMS thermal detections remain distinct from fires.
- Infrastructure adds an independent, default-off nuclear power-plant layer with
  searchable entries, clickable radiation markers and selection highlights.
- GNSS is the first category switch, with a permanent caption. Topics & time
  replaces the generic shared filter label and offers a reset for additional topics.
- Location quality explains source-reported, approximate, propagated and unplotted
  positions, with a real event-marker filter and searchable record list.
- Map style and British National Grid remain on the right, alongside drawing,
  measurement, routing and RF planning.

## OSIRIS comparison and source provenance

Reviewed OSIRIS commit `fac8d1b1dd3f9aab87bdeccdd04f05c25d5a3bb8`:

- [Earthquakes](https://github.com/simplifaisoul/osiris/blob/fac8d1b1dd3f9aab87bdeccdd04f05c25d5a3bb8/src/app/api/earthquakes/route.ts)
  uses USGS M2.5+ daily observations.
- [Weather](https://github.com/simplifaisoul/osiris/blob/fac8d1b1dd3f9aab87bdeccdd04f05c25d5a3bb8/src/app/api/weather/route.ts)
  combines NASA EONET, US NWS and GDACS cyclone/flood/drought alerts. ASE already
  collects those providers, plus EMSC and other hazard-specific feeds. This change
  exposes their distinctions rather than adding duplicate earthquake observations.
- [Infrastructure](https://github.com/simplifaisoul/osiris/blob/fac8d1b1dd3f9aab87bdeccdd04f05c25d5a3bb8/src/app/api/infrastructure/route.ts)
  contains a hand-written nuclear facility list with limited per-record sourcing.
  ASE instead packages an independently sourced WRI nuclear power-plant subset.
- [Directions](https://github.com/simplifaisoul/osiris/blob/master/src/app/api/directions/route.ts)
  uses Valhalla and a driving-only OSRM fallback. ASE uses one explicitly bounded
  Valhalla request, with no automatic fallback traffic or continuous GPS tracking.

The nuclear layer has 195 historical plant records across 31 countries. Its
[WRI source snapshot](https://github.com/wri/global-power-plant-database/tree/7a91cfbb2a4e272597acbc00506d61fc1ec73b3d)
is licensed CC BY 4.0; WRI says the database has not been maintained since early
2022. Exact source commit, CSV URL and checksum are retained in packaged provenance.
The UI shows attribution, dataset version and licence. This is not current
operational status, a reactor count, or a complete fuel-cycle/military inventory.

## Drawing and RF calculations

Draw paths, polygons, two-corner rectangles or centre/radius circles. Drawings
are local, temporary and reset on account/workspace access changes. Geometry is
bounded to 32 vertices and a 1,000 km circle radius; undo and clear are available.
Shape buttons show a recognisable symbol and the active gesture instructions.
Rectangles and circles support press-drag-release creation as well as point
clicks. Move sketch lets the operator drag an existing shape from its interior
or near its line. Cancelling a replacement preserves the previous sketch.
Pointer capture and cancellation restore map panning, and drag previews are
coalesced to animation frames. One transient sketch is retained, not an unlimited
annotation collection. Moving a circle preserves its radius; other shapes retain
longitude/latitude offsets, so measured size can change with latitude.
Measurements and drawings have exclusive click ownership. Projection changes
preserve geometry. Closing the drawing panel stops picking. Ordinary measurement
can continue with its Finish measuring readout when its panel is closed.
Disabling map tools stops both modes so they cannot resume invisibly.

Measurement foregrounds map clicks and keeps coordinate entry in a disclosure.
Active picking uses a crosshair and larger numbered point markers. Enter or
Escape finishes measurement; Backspace removes the last point, except while
editing form fields. The on-map readout exposes stop and undo actions. The
32-point bound and WGS84 surface-distance/net-area semantics remain unchanged.

The RF calculator accepts antenna heights, frequency, transmit power, gains,
losses, sensitivity and distance. It reports free-space path loss, receive level,
sensitivity margin, ideal sensitivity-limited range, standard-refraction radio
horizon and midpoint first Fresnel-zone radius. A two-point map measurement can
supply the link distance. Multi-leg path lengths are not treated as a radio link.

Nine illustrative presets supplement Custom: UHF handheld, VHF mobile/base,
marine VHF, airband VHF, UHF repeater, telemetry/LoRa, 2.4 GHz Wi-Fi, directional
5.8 GHz Wi-Fi and 6 GHz microwave. These are editable planning inputs, not
certified equipment specifications or permissions to transmit.

Place transmitter and optional receiver points on the map, then select Show
estimate on map. A purple geodesic outline shows the smaller of the ideal
sensitivity-limited distance and standard-refraction radio horizon; an optional
path joins the two sites. The outline has 73 sampled points, is not filled as a
coverage area, and is labelled as an estimate without a terrain model. Flat-map
geometry is clipped at the Web Mercator latitude limit. For directional radios,
the circle is a distance reference, not the antenna beam. Changing inputs or
positions clears the previous estimate until explicitly shown again.

Formula references: [ITU-R P.525](https://www.itu.int/rec/R-REC-P.525/en) and
[NPS radio-horizon teaching material](https://www.oc.nps.edu/NWDC_EM_Course/course_materials/module3_1.html).
No terrain, buildings, vegetation, diffraction, weather, interference or fade
margin is modelled. Ideal range and positive margin do not establish usable
coverage, Fresnel clearance or safe operational communications.

## Routing configuration and limits

The right-hand Route planner accepts two to eight stops and supports driving,
walking and cycling. Addresses and places are the default input: enter a search,
press Search and select the correct result for each stop. Coordinates are an
alternative in the Enter stops using dropdown. Existing measurement points
initialise coordinate inputs when supplied. Add waypoint inserts a stop before
the destination, and Reverse stops reverses the full journey. It returns a map line, approximate distance and duration,
and turn instructions. The route, stops, unfinished address text and travel mode
remain together while the panel is closed. Closing cancels pending requests.
Clearing, changing input or losing account/workspace access clears the route. No device location is requested.

Address search uses [Photon (komoot)](https://github.com/komoot/photon), whose
public demo allows reasonable project usage without availability guarantees.
Search text is sent only on explicit Search or Enter, never while typing. The
UI discloses the destination and asks operators to avoid confidential addresses.
This is not a public Nominatim integration. Up to five results are returned;
no-match/error states offer refinement or coordinate entry. Editing, changing
input mode or losing account/workspace access aborts stale searches.

The authenticated `POST /api/navigation/places` keeps search text out of access-log
URLs, bounds the body to 2 KiB and query to 200 characters, and admits at most one
shared request per second, with twelve per user per minute and a ten-second
deadline. The fixed HTTPS provider uses the existing protected transport, without
redirects or address-bearing diagnostics. Results are transient, bounded and
validated, and the session is rechecked after provider work. The shared HTTP
transport caps response intake at 2 MiB; the Photon parser rejects more than
128 KiB before JSON decoding. Photon needs no API
key. Larger use requires a provider arrangement suitable for that traffic.

Only Calculate route transmits waypoints to FOSSGIS. Routes are not persisted;
the provider may log requests. The UI states this and includes OSM attribution,
ODbL, Fix the map and provider terms. An operator must configure a real public
`ASE_FEEDS_CONTACT` email: placeholders disable routing before external access.
This setting is currently a local operator configuration, not a new admin page.

[FOSSGIS usage terms](https://fossgis.de/arbeitsgruppen/osm-server/nutzungsbedingungen/)
permit modest third-party integrations, not heavy production traffic. The current
single-process deployment enforces one shared in-flight request, at most one per
second and six per user per minute. Input is limited to 4 KiB, response to 2 MiB,
20,000 route coordinates and 500 instructions, with a 15-second request deadline.
Walking requests are limited to 100 km endpoint-path length and other modes to
1,000 km. These are planning estimates, not authoritative or safety-critical
navigation. A larger deployment requires a suitable routing provider arrangement.

Security review checked fixed provider origin, public DNS pinning, no redirects,
coordinate-bearing log suppression, bounded parsing, authentication before intake,
and session revalidation after egress. No paid account, new dependency, database
migration or production deployment was introduced. Live routing cannot be claimed
until the operator contact is configured and a provider request succeeds.

Interactive GPU verification remains unavailable under the existing browser
policy block. Mocked globe/map interaction tests do not establish a visual soak test.


## Ordnance Survey style readiness

OS Road, OS Outdoor and OS Light remain unavailable without the server-side
`ASE_OS_MAPS_KEY`. The current local configuration has no OS key. The style panel
now groups these choices with a visible readiness state, setup instructions and
Check configuration again. It distinguishes checking, failed capability lookup,
unconfigured and configured states. A configured key is not a successful tile
probe. Keys stay on the server; an administrator must add a suitable OS Data Hub
Maps API key and restart the API. OS coverage is Great Britain at zoom 7 to 16;
the independent BNG overlay does not require those basemaps.

## Earlier map-tools validation record

- Full frontend suite: 1,327 tests across 269 files passed; 95.27% statements,
  90.29% branches, 93.54% functions and 96.60% lines. Coverage thresholds unchanged.
- Final hazard taxonomy and navigation-schema adjustments: 23 focused tests passed.
- TypeScript, full ESLint and production build passed. Existing large map-library
  chunk advisory remains; no dependency or GPU event-limit increase was introduced.
- Final combined backend navigation, nuclear and event API checks: 40 tests passed.
  Nuclear normalisation tests measured 100% scoped branch coverage.
  Routing tests cover parsing bounds, admission, cancellation, authentication,
  contact readiness and session revocation during provider work.
- Backend static analysis and both architecture contracts passed. File-length and
  whitespace checks passed. Configured secret matching found no values in tracked
  or proposed repository files.
- Authenticated local API verification returned 195 nuclear records across 31
  countries. The frontend login returned HTTP 200. Routing capabilities correctly
  reported unavailable while the public operator email remains unconfigured.
- Mocked integration tests cover grouped disclosures, shape persistence across
  projections, exclusive click ownership, disabled-tool reset, route clearing and
  nuclear selection/close highlights. Live routing and GPU soak tests remain open.


## Interaction and address-search follow-up verification

Drag previews update only drawing layers. Measurement, RF and route layers have
independent memoisation, so a sketch drag does not repeatedly resample unchanged
geodesics or upload an unchanged route. A regression uses a 20,000-coordinate
route and verifies layer/data identity through previews and commit, while
projection and route changes still refresh the relevant geometry. Drawing
handles also avoid calculating a second, discarded geodesic path.

Initial focused route checks passed seven frontend tests and twenty-eight backend
navigation/place-search tests. The new geocoding modules measured 94% scoped
coverage; targeted ESLint/Ruff, frontend types, scoped mypy and both backend
architecture contracts passed. These checks cover explicit search, selecting
results, stale response cancellation, coordinate fallback, reverse stops,
bounded parsing, admission, authentication and session revocation during lookup.
Follow-up regressions cover closing/reopening with a matching draft/result,
clearing after edits or an account change, and retaining unfinished address text
without launching a search. They do not establish live provider availability.

Final combined verification on 9 September 2026:

- 1,425 frontend tests passed across 286 files; one opt-in stress test was skipped.
  Coverage: 95.48% statements, 90.49% branches, 93.71% functions, 96.78% lines.
  Coverage gates were unchanged.
- 33 backend navigation, place-search and OS tile regressions passed. Scoped
  geocoding coverage was 94% in the earlier focused run.
- TypeScript, full ESLint, production build and changed-file Prettier passed.
  Scoped Ruff, mypy and Bandit passed; both architecture contracts were kept.
  Whitespace and file-length checks passed. The engine orchestration remains
  380 lines against the 400-line ceiling, with pointer handling extracted.
- Review checked session revalidation, address privacy, bounded provider work,
  cancellation and map-layer identity. Four configured secret values were
  checked without disclosure; none matched the proposed changes.
- The restarted local ASE API returned 200 for health/readiness, registered
  the place-search endpoint and returned 401 to an unauthenticated lookup.
  The frontend at port 5174 returned 200. No live provider lookup was claimed.
- Existing large vendor-chunk build warnings remain. The three pre-existing
  repository-wide formatter failures listed in GNSS_AND_MAP_CONTROLS.md were
  not part of the changed-file formatting check.

Live OS tile delivery still needs a configured key. Route calculation still
needs the operator contact described above. RF estimates do not model terrain
or establish actual reception. Interactive browser/GPU validation remains blocked
by the existing administrator policy; tests using a mocked map engine are not an
observed usability or graphics-driver soak test.

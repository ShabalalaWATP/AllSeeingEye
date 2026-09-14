# Map layers and planning tools

Updated 10 September 2026.

## Operator controls

On a fresh page load or reload, only Conflict & unrest is visible. Flights, ships,
FIRMS, space, hazards, news and other topics start hidden; CCTV, infrastructure,
GNSS, BNG and day/night shading also start off. Older saved day/night and GNSS
preferences no longer reactivate those layers. Basemap and lite-mode preferences
remain saved. Operators can enable other layers for the current session.

Conflict controls now include a searchable regional overview alongside individual
report filters. See [conflict display controls](CONFLICT_DISPLAY_FILTERS.md).

- Space is one left-rail category. Its filter disclosure contains the existing
  satellite catalogue choices. There is no separate satellite-filter rail icon.
- Conflict reports have a crossed-swords symbol and filters for reported type,
  text, source and location precision. Historical monthly baselines remain opt-in.
  Counts describe loaded reports, not verified or independently unique incidents.
- Natural hazards have their own category disclosure with hazard type, acquisition
  or report time, explicit earthquake magnitude and GDACS impact-level filters.
  Unknown measurements can be retained; magnitudes are not inferred from another
  provider's severity scale. **Fires** combines reported wildfires and satellite
  heat detections, with nested choices for each. Orange flame symbols identify
  wildfire reports; FIRMS retains its sensor symbol and independent display switch.
  Choosing Fires leaves hidden layers off and does not equate detections with
  independently confirmed fires. See [FIRMS operations](FIRMS_OPERATIONS.md).
- Infrastructure adds an independent, default-off nuclear power-plant layer with
  searchable entries, clickable radiation markers and selection highlights.
- GNSS is the first category switch, with a permanent caption. Topics & time
  replaces the generic shared filter label and offers a reset for additional topics.
- Location quality explains source-reported, approximate, propagated and unplotted
  positions, with a real event-marker filter and searchable record list.
- Map style and British National Grid remain on the right, alongside drawing,
  measurement, routing and RF planning.

## Compact tool panels

Map tools share a dark drawer with an icon, clear title, close action and internal
scrolling. General drawers are at most 320 px wide; drawing, measurement, routing
and RF are at most 360 px. Narrow-screen widths leave space for the rails. Escape
and Close return focus to the opening button. Controls remain non-modal so map
gestures are available. Reduced-motion preferences disable the brief transitions.

- Measurement offers labelled Distance/Area choices, a prominent result and
  one Pick/Finish action. Manual coordinates, coordinate history and accuracy
  notes are expandable. Its existing map-picking shortcuts remain unchanged.
- Drawing uses labelled shape icons showing their defining points. Creation,
  move, undo and clear remain separate actions, with active gesture instructions.
- Routing shows driving/walking/cycling choices, numbered stops, selected address
  matches and separate distance/time results. Selecting a match returns keyboard
  focus to its address field. Search and routing disclosure remain visible before
  requests; directions and provider terms are expandable.
- Map style opens its choices immediately in the shared drawer. Swatches are
  local illustrations, not fetched previews. Disabled OS options retain their
  configuration explanation. Selected imagery age, source and licence remain
  outside the optional setup disclosure. Appearance and BNG have labelled switches.
- Location quality puts filtering, search and matching records before the
  classification glossary. The active quality explanation and unplotted-record
  warning remain visible. Nation results say "loaded", avoiding a freshness claim.
- Topics & time puts time choices first and uses labelled switches for additional
  topics. Aircraft/vessel filters retain native radio semantics with clearer
  selected states, consistent fields and pagination controls.

Existing CCTV, infrastructure, satellite and context grouping remains intact within
the shared drawer. Invalid conflict/hazard/context field colour tokens were replaced
with actual theme tokens. This presentation update adds no provider requests,
background loops, dependencies, map calculations or persistence changes.

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
is licensed CC BY 4.0; WRI says the database has not been maintained since early 2022. Exact source commit, CSV URL and checksum are retained in packaged provenance.
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

The RF calculator now separates three propagation choices from the free-space
reference: Terrain-aware VHF/UHF, HF groundwave and HF skywave scenario. The
operator chooses a model, editable equipment inputs and environmental assumptions,
places the transmitter and optional receiver, and explicitly starts the first
analysis. Automatic setup chooses the model and area extent, with manual
overrides. Optional automatic updates then respond to valid edits with a
1.2-second debounce and at least 30 seconds between automatic attempts, measured
from the last manual or automatic attempt. There is no polling or initial work.
Changing inputs or positions invalidates the previous result. No extra polling
or calculation on every keystroke is introduced.

The free-space reference retains ideal path loss, receive level, sensitivity
margin, standard-refraction radio horizon and first Fresnel-zone radius. Its
outline uses the smaller ideal sensitivity distance and radio horizon. An optional
shaded 360° reference uses that same limit; it does not establish reception.
See [ITU-R P.525](https://www.itu.int/rec/R-REC-P.525/en).

### Terrain-aware VHF/UHF

Terrain analysis uses bounded requests for Mapzen Terrain Tiles in Terrarium
format, sampled at zoom 10. It adds each antenna's above-ground height to its
sampled source elevation. Elevation above sea level and antenna height above
ground are displayed separately; changing an antenna's height does not change
the underlying ground elevation.

A two-site study targets roughly 100 m intervals, capped at 769 points along a path of at most 200 km, and
shows a terrain profile. The selectable 360° area study screens 24 bearings
with 17 outward steps concentrated nearer TX, at most 409 positions per request
within a 50 km radius. Automatic area planning can make one additional pass,
retaining both passes' observations inside the final extent, at most 817 unique
positions. The panel caches two complete, exactly matching elevation batches for
five minutes from fetch and clears them on account/access changes or unmount.
These are
coarse samples, not a dense coverage raster. The screen defaults to k=4/3
Earth curvature, 60% first Fresnel clearance and free-space loss plus a single
dominant sampled knife-edge diffraction term. It is not a complete ITM or
ITU-R P.526 implementation. A radial stops at the first sampled obstruction,
clearance restriction, insufficient planning reserve or missing point. Optional shading
between adjacent passing bearings is explicitly illustrative; those gaps remain
unassessed. See [RF reach and coverage display](RF_COVERAGE_DISPLAY.md) for the
colour key, obstruction distances, per-bearing limits and display controls.

The authenticated `POST /api/terrain/elevations` bounds intake to 64 KiB, at most
1,000 positions and 64 unique tiles. There are at most two active requests, six
requests per user per minute and twelve shared provider requests per minute.
Fixed provider origins, bounded image decoding and session revalidation protect
the request path. Missing elevations cause an explicit unavailable result,
never substituted flat ground. Negative elevations remain negative, including
possible bathymetry; a water-surface model is not inferred. Source attribution,
nominal resolution and mixed historical DEM limitations accompany results.

The optional uniform obstacle-height screen does not detect actual trees or
buildings. The operator can edit effective Earth factor and required reserve;
the UI defaults to 10 dB reserve, without claiming a reliability percentage.
Terrain sampling does not measure weather, interference, antenna patterns or
fading. A sampled clearance pass is not reliable reception.
Provider details: [Mapzen terrain sources](https://github.com/tilezen/joerd/blob/master/docs/attribution.md).

### HF models and equipment references

HF groundwave calls the official, pinned NTIA LFMF 1.1 native solver through the
authenticated `POST /api/radio/groundwave`. The application supports 1.6 to 30 MHz,
0 to 50 m antenna heights above ground and operator-entered conductivity,
permittivity and refractivity. Its bounded curve reports basic transmission loss,
native reference field and received power with the user's gains and losses.
The map contour assumes homogeneous smooth Earth. It is independent of terrain
screening and is not measured reception. See [HF groundwave model](HF_GROUNDWAVE_MODEL.md)
for normalisation, reference vectors, licence, capacity and limits.

HF skywave is an operator-defined single-hop geometry scenario using assumed
foF2, virtual-layer height and launch-angle limits. Inner and outer map rings
describe that scenario and its simplified frequency gate. There is no live
ionospheric feed, forecast, received-signal calculation, absorption model or
real ray tracing. Transmit power and mast height alone do not determine launch
angles or the rings. The UI explicitly distinguishes this from groundwave.

The grouped catalogue now has 25 choices, including four Bowman scenarios,
AN/PRC-150(C), PRC-152A, PRC-117G, Thales PRC-148, SINCGARS RT-1702 and the existing
RF-5800H-MP. General VHF/UHF, marine, airband, telemetry and Wi-Fi examples remain.
Bowman frequency/power selections are labelled assumptions; manufacturer-backed
equipment entries show published bands and mode-specific output ratings separately
from editable planning inputs. See [radio presets](RADIO_PRESETS.md) for exact
choices, references and validation. All presets remain editable and range is an estimate.

### Infrastructure and CCTV catalogue usability

Historical WRI source URLs can use HTTP. The frontend previously required HTTPS
for every source-reference field, rejecting the complete infrastructure payload
when one historical URL did not qualify. That field now accepts valid HTTP or
HTTPS source references while still rejecting credentials, explicit ports and
other schemes. These are outbound attribution links, not app-fetched media.
Other catalogue URL requirements are retained. Requests and loaded infrastructure
state are cleared on account/workspace access changes; the API rechecks session
access before returning a catalogue.

Infrastructure controls and CCTV source groups use clearer switches, spacing,
search prompts and empty/error states. Camera rows identify provider, available
snapshot/video/provider-page media, approximate positions and current selection.
Searching returns the list to its first page; lists remain bounded and scrollable.
Media remains selection-driven and this redesign adds no polling or new camera
providers. Source coverage and provider availability are not expanded by styling.

### Public figures layer

The "Public figures" panel on the left rail toggles an off-by-default layer of
circular portraits for current office-holders, ringed by placement basis. Selecting
a portrait or a list entry flies to the placement and opens an inspector that
explains the basis and lists the reporting behind it. See
[Public figures](PUBLIC_FIGURES.md) for the roster, doctrine and import.

## Routing configuration and limits

The local development contact was configured in the ignored backend environment
on 9 September 2026 using the operator-provided email. The API was restarted.
The Valhalla request now uses percent-encoded JSON spaces: form-style `+` spaces
caused the public service to return HTTP 400. The protected HTTP transport,
fixed host, coordinate-log redaction, byte bounds and rate limits are unchanged.
A single public London walking-route probe through the application adapter
returned 1.1 km, 114 geometry points and 24 instructions. This verifies that
request path, not route safety, terrain accuracy or uninterrupted availability.

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
needs the operator contact described above. This earlier validation covered the
free-space RF reference; the terrain/HF follow-up is recorded below. No RF mode
establishes actual reception. Interactive browser/GPU validation remains blocked
by the existing administrator policy; tests using a mocked map engine are not an
observed usability or graphics-driver soak test.

## Terrain, HF and catalogue follow-up validation

The final frontend suite passed 1,513 tests, with one existing skipped test:
95.40% statements, 90.21% branches, 93.42% functions and 96.67% lines. Both map
projections are covered with a mocked engine. Regression checks include stale
analysis cancellation, A-to-B-to-A input changes, preset transitions, DEM plus
AGL heights, bounded HF interpolation and camera/infrastructure selection after
removing the updates bar. Full ESLint, TypeScript and production build passed.
Existing large vendor-chunk warnings remain.

The combined backend run passed 49 terrain, groundwave and infrastructure tests.
Separately measured terrain coverage was 98.03%; groundwave coverage was 100%
for statements and branches, including five published NTIA reference vectors.
Scoped Ruff, Bandit, full backend mypy and both architecture contracts passed.
Changed-file formatting, whitespace and file-length checks passed. Review checked
bounded native work, fixed terrain destinations, request/session cancellation,
source-link handling and numerical assumptions. No configured secret values
were found in the proposed files.

A public London terrain tile downloaded and decoded successfully. This verifies
provider transport and decoding, not elevation accuracy. After restarting the
local ASE API, health/readiness returned 200 and both new protected endpoints
returned 401 without authentication. The frontend on port 5174 returned 200.
An authenticated interactive terrain flow and GPU/visual acceptance remain
unverified because the existing administrator browser-control policy blocks
interactive checks. Automated tests do not establish measured RF reception.

## Dashboard refinement, 10 September 2026

Traffic drawers now share the main panel owner. Text and provider filters apply to
map and list together, and the event-scope strip keeps active refinements visible.
Space includes searchable satellite results and an on-demand NOAA weather tab.
Boats includes NAVAREA warnings; Network opens IODA signal context. CCTV supports
stream, clip, snapshot and provider-link filtering. Selected objects show readable
facts before raw source fields. Completed drawings can hand off a conservative,
editable bounding rectangle to the existing Warning indicator form, with reports
off by default. See [dashboard context and watches](DASHBOARD_CONTEXT_AND_WATCHES.md)
for exact scope, performance, access limits and remaining work.

## Research area

The right-hand toolbar includes **Research area**. Draw a polygon, rectangle or
circle, optionally ask a question, check source support and generate a personal
AI report. It preserves the exact boundary and collection period, with cited
evidence and source coverage receipts. Drawing and research have separate state
and share the exclusive map-input owner with measurement and RF tools.
See [area research](AREA_RESEARCH.md) for the full flow, bounds and limitations.

## Technology and communications control, 13 September 2026

One rail control now owns undersea cables, satellite ground stations, data centres and
semiconductor sites, with the connectivity signals panel on a second tab. The
Infrastructure control keeps nuclear power, oil and gas facilities and the military
source index. Both controls render the same panel component over the same
infrastructure state, narrowed by a `group` prop, so a selection made from one is
still highlighted when the other is open. The standalone Network button left the rail;
the network map's country markers now load while the connectivity tab is open, which
the tab reports to the map through a callback rather than by panel label.

## Ukraine war page, 13 and 14 September 2026

The left rail gained "Ukraine war" (`/conflicts/ukraine`), a scrolling workspace rather than a
globe layer: a 2D mercator map of reported control from VIINA 2.0 over geoBoundaries
oblasts, provider frontline layers behind operator flags, grouped updates with lenses,
claimed, visually confirmed and documented figures, a timeline, force trees and an equipment
catalogue. `docs/UKRAINE_WAR_TRACKER.md` describes it; `docs/UKRAINE_WAR_TRACKER_PLAN.md`
records the source research. The globe's Conflict panel and Frontlines directory are
unchanged and still list the access routes for DeepState, ISW and OCHA.

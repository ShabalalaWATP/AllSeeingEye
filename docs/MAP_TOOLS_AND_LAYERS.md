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
Measurements and drawings have exclusive click ownership. Projection changes
preserve geometry. Closing the drawing panel stops picking. Ordinary measurement
can continue with its existing Stop measuring readout when its panel is closed.
Disabling map tools stops both modes so they cannot resume invisibly.

The RF calculator accepts antenna heights, frequency, transmit power, gains,
losses, sensitivity and distance. It reports free-space path loss, receive level,
sensitivity margin, ideal sensitivity-limited range, standard-refraction radio
horizon and midpoint first Fresnel-zone radius. A two-point map measurement can
supply the link distance. Multi-leg path lengths are not treated as a radio link.

Formula references: [ITU-R P.525](https://www.itu.int/rec/R-REC-P.525/en) and
[NPS radio-horizon teaching material](https://www.oc.nps.edu/NWDC_EM_Course/course_materials/module3_1.html).
No terrain, buildings, vegetation, diffraction, weather, interference or fade
margin is modelled. Ideal range and positive margin do not establish usable
coverage, Fresnel clearance or safe operational communications.

## Routing configuration and limits

The right-hand Route planner accepts two to eight coordinate waypoints and
supports driving, walking and cycling. Existing measurement points initialise
its inputs when opened. It returns a map line, approximate distance and duration,
and turn instructions. Clearing, changing input, closing the panel or losing
account/workspace access clears the route. No device location is requested.

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


## Validation record

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

# Dashboard feature and filter review

Compared 9 September 2026. Delivery status updated 10 September 2026. Checked items
below identify implemented software, with validation and limits in the delivery note.

## Evidence and scope

Compared ASE at `fa69747` with OSIRIS master
[`11ecf488`](https://github.com/simplifaisoul/osiris/tree/11ecf488253c202714ab11709750b651c765e07b),
which the GitHub tree API returned during this review. Inspected its actual layer
panel, map, dashboard composition, watch tools, GIS importer and selected adapters.
The live demo fetch timed out; no fresh interactive visual inspection is claimed.
The user's earlier screenshot remains a visual reference. ASE's existing browser
policy also prevents current interactive/GPU acceptance.

ASE code, rather than older completion notes, establishes the comparison below.
The strongest opportunity is to connect existing research and collection features
to the live dashboard and make each category behave consistently.

## What OSIRIS provides

| Observed implementation | Useful lesson for ASE |
| --- | --- |
| Narrow icon rail; category flyouts open on hover and can be pinned by clicking; active-subtype badges; group all/none actions | Compact entry points with an explicit, stable open state |
| Named subtype switches, indented dependent options and item counts | Consistent hierarchy and clear parent/child relationships |
| Commercial/private/jet/military aircraft and mission-based satellite categories | More useful discrimination within the existing transport and space categories |
| Several aircraft can be pinned with telemetry, route/trail detail and map location controls | A small shortlist helps compare selected objects without repeatedly losing selection |
| Named drawings, area contents, local arrival/departure watches and GeoJSON export | Drawn areas should lead to useful research and changes, not just a coloured outline |
| Right-click place dossier using reverse geocoding, Wikipedia and Wikidata | Make place research accessible directly from the map |
| ArcGIS dataset search, topic shortcuts, bounds-aware queries and imported-layer visibility/colour/opacity | A controlled public dataset browser would expand useful infrastructure coverage |
| Search with result-specific zoom, regional bookmarks, optional terrain/buildings and a style editor | Improve navigation and legibility without adding another permanent dashboard panel |

Sources: [layer panel](https://github.com/simplifaisoul/osiris/blob/11ecf488253c202714ab11709750b651c765e07b/src/components/LayerPanel.tsx),
[flight watch](https://github.com/simplifaisoul/osiris/blob/11ecf488253c202714ab11709750b651c765e07b/src/components/FlightWatchPanel.tsx),
[dashboard wiring](https://github.com/simplifaisoul/osiris/blob/11ecf488253c202714ab11709750b651c765e07b/src/app/page.tsx),
[area change logic](https://github.com/simplifaisoul/osiris/blob/11ecf488253c202714ab11709750b651c765e07b/src/lib/watch.ts),
[place dossier](https://github.com/simplifaisoul/osiris/blob/11ecf488253c202714ab11709750b651c765e07b/src/app/api/region-dossier/route.ts),
[GIS panel](https://github.com/simplifaisoul/osiris/blob/11ecf488253c202714ab11709750b651c765e07b/src/components/ArcGISPanel.tsx).

Do not assume that every README entry or API route is an active, working map
control. For example, its air-quality route still requests OpenAQ v2, which
[OpenAQ documents as retired](https://docs.openaq.org/about/about). A new integration
would require v3 and its [API-key workflow](https://docs.openaq.org/using-the-api/api-key).
Its space-weather route also assigns G1 at Kp 4; the
[official NOAA scales](https://www.spaceweather.gov/noaa-scales-explanation)
start G1 at Kp 5. Reuse the interaction ideas and verify each data interpretation.
See the [existing conflict audit](CONFLICT_RELEVANCE_SCREENING.md) for the separate
problem of keyword matching and approximate regional dots.

## Existing ASE capabilities and actual gaps

| Area | Present in current code | Proposed extension |
| --- | --- | --- |
| Flights and ships | Shared panel, All/Military, shared map/list search and provider filter; aircraft ground-status filter; paginated locate and readable selected facts | Class/operator, altitude/speed and observation-age filters; small pinned shortlist; selected history where genuinely available |
| Space | All, crewed, public military and Skynet; name/NORAD/designator search and locate; orbital facts; NOAA context tab | Mission/constellation/orbit filters using actual metadata; orbit/pass detail |
| Natural hazards | Earthquake, weather/cyclone, flood, volcano, wildfire, thermal, tsunami, drought, landslide and ice choices; magnitude/time/GDACS severity | Multi-select types, warning-area polygons, cyclone paths/cones and a clearer time scope |
| GNSS | Dedicated control, flag/observation filters, cell details and freshness | Compare reports over a supported time window; useful links to aviation and space-weather context |
| Infrastructure | Cables, satellite ground stations, historical nuclear power catalogue and text search | Public airports, ports and chokepoints; selected energy/communications datasets with per-source dates |
| CCTV | Provider/region choices, provider-name search, clusters, stream/clip/snapshot/provider-link filters | In-view/availability filters, favourites and a small operator-opened comparison panel |
| Conflict | Curated regions, screened source reports, type/source/text/precision and explicit historical/unreviewed options | Better incident/region distinction, grouped reporting and linked map/list selection |
| Place research | Research action on selected events; completed sketch hands off an editable rectangular count watch | Actual area-scoped collection, cited area briefs and place dossiers |
| Saved maps | Report-associated map revisions, timeline, AOIs and research handoff | A proper live-dashboard saved-view contract and reusable investigation presets |
| Weather/connectivity | On-demand dated NOAA scales/Kp/bulletins, IODA signals and NAVAREA panels; first-position warning selection | Warning-area geometry and other supported weather context |

Current code references:

- `frontend/src/features/globe/GlobePage.tsx`, `MapLayerRail.tsx`,
  `GlobeControls.tsx`, `MapReferencePanels.tsx`, `LayerPanel.tsx`.
- `frontend/src/features/globe/FlightLayerControl.tsx`, `SatelliteFilterPanel.tsx`,
  `HazardFilterPanel.tsx`, `ConflictFilterPanel.tsx`, `EventInspector.tsx`.
- `frontend/src/components/maps/ReportEvidenceMap.tsx` and related area/saved-map controls.
- `frontend/src/lib/api/events.ts`, `frontend/src/stores/events.ts`.
- `backend/src/ase/adapters/feeds/registry.py`,
  `backend/src/ase/application/feeds/budgets.py`,
  `backend/src/ase/application/warning/indicators.py`.

The dashboard now gives traffic and category tools one panel owner. Active event
scope and removable refinements remain visible after closing a drawer. Topics/time
explains the separate catalogue, regional and context scopes. Aircraft, vessels,
satellites, earthquakes and FIRMS now have readable source-backed facts, with raw
attributes under a collapsed Source fields disclosure. Other categories can still
benefit from specialised facts and a more uniform source-status treatment.

## Proposed filter and dashboard design

Keep the near-black canvas, restrained cyan active states and existing rail sizes.
Improve spacing, contrast and behaviour within that design. Keep only Conflicts
enabled on a fresh/default view. Loading an explicitly saved view is a separate,
deliberate action. Do not reintroduce the removed scrolling event ticker.

### Placement

- **Left:** information categories. Conflicts, Air, Sea, Space, Cameras, Hazards,
  GNSS, Infrastructure and Connectivity, with additional categories in a searchable
  More menu. News can be added there and pinned if useful. Avoid another tall rail.
- **Right:** map appearance, BNG/grid, measure, draw, routes and RF tools. Saved
  views/export can live in a compact overflow. No duplicate category switches here.
- **Top:** a compact place/object search, optional area-research action and removable
  scope chips. Preserve map/globe controls. No permanent large summary card.
- **Bottom:** existing quiet clocks/coordinates and attribution; an optional time
  drawer opens upwards. A small Data status control opens provider health on demand.

### One category panel pattern

Click opens a stable panel; hover/focus shows the full category label. One category
panel at a time, without a second independently portalled flight popup. Use the
same contents in a mobile sheet, with keyboard focus and Escape handling.

1. Header: category name, visibility switch and explicit data state.
2. Types: multi-select checkboxes where types can coexist; segmented controls for
   genuinely exclusive modes. Parent switches retain chosen subtypes when disabled.
3. Refine: domain-specific fields, clear/reset and text search when useful.
4. Results: Map/List choices sharing the same selection and filtered results.
5. Source and coverage: expandable provenance and limitations. Stale, offline and
   unconfigured states remain visible beside the switch, not buried in help text.

Separate visibility from filtering. Prefer **Show on map**, **Types** and
**Refine results** over several controls all called Layers, Settings or Filter.
Group actions should be labelled Show all/Hide all and Reset filters separately.
An all-off type set means no results, never an implicit all-on fallback.

An aircraft panel could read:

```text
AIR TRAFFIC                          Show on map [on]
This view · 42 matching · updated 18 seconds ago

Types       [x] Military  [ ] Commercial  [ ] Other/unknown
Search      Callsign, registration or operator
Age         Last observed within [5 minutes]
Altitude    [Any]              More filters

Map | List                   Reset filters
Source and coverage          2 providers · partial coverage
```

Counts in this example are illustrative. Define whether counts mean available,
loaded, matching or individually rendered objects. Do not present a loaded count
as the worldwide population or as a promise of complete sensor coverage.

### Shared scope and useful subtype filters

| Category | Most useful additional controls |
| --- | --- |
| Air | Aircraft class, operator/registration, airborne/on-ground, altitude, speed, age and provider; keep unknown military status explicit |
| Sea | Vessel type, reported flag, status, age, speed and provider; separate ship positions from ports and navigation warnings |
| Space | Name/NORAD, mission, orbit class, constellation and orbital-element age; only expose supported metadata |
| Cameras | Current view/nation, snapshot/stream/external, provider and availability; unknown image capture age stays unknown |
| Hazards | Multiple hazard types, magnitude/depth, alert severity, active/expired and event/issue time |
| Conflicts | Regional context versus reported incident, violence type, source, relevance-review status, date and location precision |
| GNSS | Provider window, report level and observation support; coverage gaps visible; cells do not locate a jammer |
| Infrastructure | Facility type, nation, publisher, dataset date and search; catalogue status stays separate from a live operational assessment |
| News | Topic, publisher, original language, reporting period and location precision; distinguish story location from broadcaster location |

The common strip should make **This view / Nation / Worldwide** and the selected
time window obvious. Nation means geographic location unless a control explicitly
says vessel flag, aircraft registration or operator country. Every filter chip
shows its scope, such as Event time:24h or Aircraft observed:5m. Static catalogues
must explicitly say that the event-time filter does not apply. Source grade,
model relevance and claim confidence are different measures, not one accuracy slider.

## Prioritised additions

### Milestone 1: clearer interaction using existing data

- [x] Shared panel ownership and visible active event scope. Further category layout
  and source-status consistency remain useful refinements.
- [x] Specialist aircraft, vessel, satellite, earthquake and FIRMS facts with retained
  units, source dates and unknown values. Severity is explicitly distinct from accuracy.
- [x] Shared map/list traffic search and provider filters, aircraft status, satellite
  search/locate and camera media filters.
- [ ] Camera in-view/availability filtering and remaining traffic numeric filters.
- [x] Dedicated Space weather view: existing Kp, NOAA R/S/G, dated alerts and relevant
  HF/GNSS context. Keep it distinct from terrestrial interference and the RF model.
- [x] Connectivity signals and navigation warnings surfaced from existing adapters.
  IODA records are not a current-outage inventory; NAVAREA markers are first reported
  positions, not warning-zone geometry.

Success: the operator can see what is enabled, why an object is missing and when
the displayed data was observed without opening several unrelated panels.

### Milestone 2: make the dashboard useful for research

- [x] **Watch this area** from completed drawings, with an editable conservative
  bounding rectangle, count threshold and reports off by default. Handles dateline
  bounds and geodesic edge curvature. This is not arrival/departure detection.
- [ ] **Brief this area** and **Research a question** with genuine spatial collection
  scope. The current arbitrary dashboard geometry has no report-revision identity;
  putting coordinates in question text is not a substitute for a collection contract.
- [ ] Area brief contains recent developments, source disagreements, nearby relevant
  objects and coverage gaps, with citations and a Save report action. Model calls
  are explicit and budgeted; a usable administrator-assigned model is required.
- [ ] Saved dashboard views containing camera position, categories, filters and AOIs,
  with basic personal/team sharing. Suggested templates: aviation, maritime,
  hazards and a user-defined region. Templates are opened deliberately.
- [ ] Pin a small aircraft/vessel shortlist with compare/locate/follow. Mark missing
  or stale telemetry; do not invent a path between sporadic observations.
- [ ] Paused inspection, with a visible paused time and explicit return to current
  data. Freeze the view consistently, not the shared collection worker for everyone.

The existing report map uses exact report revisions. Do not fabricate a report ID
to reuse it: dashboard views need their own appropriate owner/scope/state contract.
Area watches must distinguish a feed loss from an object leaving the area. Existing
warning thresholds/cooldowns are a foundation, not complete crossing detection.

### Milestone 3: selected new layers and deeper map context

- [ ] Curated public GIS browser: preview publisher, licence, extent and dataset
  date before adding bounded features. Start with official public port/airport and
  relevant infrastructure datasets; support selected ArcGIS services through the
  existing outbound guard. A portal listing alone does not establish reliability.
- [ ] Dated weather warning polygons and cyclone tracks/cones using supported
  provider geometry. Wind, cloud and precipitation rasters are additional provider
  work, with observation/forecast times and geographic coverage labelled.
- [ ] Curated live broadcaster directory and nearby news list, opened on demand.
  Broadcaster locations do not become incident coordinates. Keep Telegram outside
  the current accepted source scope unless that product decision changes.
- [ ] On-demand terrain/buildings, hillshade/contours, imagery date comparison and
  satellite orbit/pass information where supported. Disable unsupported projection
  combinations with a useful reason. Current RF elevation analysis is not 3D terrain.
- [ ] Actual bounded history and time scrubber only after retention/provider rights
  are designed. Existing current-position caches cannot provide historical replay.

Later candidates: air-quality stations, dated public radiation monitoring, local
infrastructure disruption and sanctions enrichment on an already selected entity.
These need their own source/identity/coverage checks. Markets tickers, cosmetic
attack arcs and device-control consoles are low priorities for this product.

## Delivery and performance acceptance

Keep the existing shared map renderer and browser memory caps. The browser event
store has a 5,000-item bound and the backend keeps latest traffic observations in a
bounded cache. New history must not be implemented by quietly removing those limits.

- No new heavy layer loads on startup; only conflicts are enabled by default.
- Reuse cached data and existing sources before creating new collection loops.
- Fetch displayed geography where supported, with visible provider coverage limits.
- Debounce expensive inputs; cancel obsolete requests and avoid rebuilding every
  map layer when one category filter changes. Bound GIS geometry and selected trails.
- Show camera media only on selection or explicit comparison; pause hidden media.
  Put strict concurrency and memory limits on any comparison panel.
- Draw selection, list selection and inspector use the same filtered dataset.
  Closing details clears selection. Filtering it out produces an explicit state.
- Test globe/flat parity, changed map style, country/dateline edges, empty/offline
  providers, reset-to-default, keyboard/mobile controls and repeated layer toggles.
- Compare responsiveness and memory before/after under the same representative
  dense datasets. Browser/GPU acceptance remains a separate required check.
- New public-dataset fetches need existing SSRF controls, bounds, publisher/licence
  review and cancellation. New shared saved objects require object-level access checks.

The original review was documentation only. The 10 September implementation reuses
existing providers and introduces no dependencies, credentials, background polling
or model calls. See [dashboard controls and context](DASHBOARD_CONTEXT_AND_WATCHES.md)
for the shipped behaviour, remaining work and validation record.

# GNSS interference and map controls

Implemented locally on 9 September 2026. GNSS is an independent map presentation
category, using the existing authenticated aviation accuracy endpoint. It does
not require a new provider account or database migration. Since 13 September the
cyber workspace reads the same endpoint and groups amber and red cells into
named regions for reading; see `CYBER_THREAT_INTELLIGENCE.md`.

## Where controls live

| Location | Purpose |
| --- | --- |
| Left category switches | Show or hide flights, boats, FIRMS, Space, natural hazards, conflict reports, news and GNSS. |
| Filters beneath a category | Options and lists for that category. GNSS has severity and minimum-observation filters, with selectable cells. |
| Left Topics & time | Additional topics (cyber, social, political, humanitarian and economic), Show all topics, shared event time window and clear-time action. Connection, coverage and reload details expand on demand. |
| Left CCTV and Infrastructure | Catalogue selection and visibility. |
| Right Map style | Basemap, day/night shading and reduced graphics. Reduced graphics temporarily suppresses day/night shading, atmosphere and rotation. |
| Right British National Grid | BNG overlay and grid tools. |
| Right navigation and planning | Find nation, Location quality, drawing, routing, RF calculations and measurement. |

The former Layers and settings panel repeated category and appearance controls.
Those copies have been removed. The shared panel is now called Topics & time,
with a topic-list symbol rather than another funnel. GNSS is the first category
switch and keeps its visible GNSS caption. The rails have visible scrollbars and
buttons no longer shrink when the available height is limited. Category-specific filters further narrow the
shared event time window. GNSS has its own aggregate; CCTV and infrastructure
have their own catalogue coverage. The natural-hazard group includes FIRMS,
whose separate switch controls the thermal-detection subset. The hazard panel
now explains that relationship.

## What GNSS represents

The overlay shows an ASE-derived proxy from aircraft ADS-B navigation-accuracy
reports (`nac_p`). It is not an imported GPSJam dataset. Available reports are
binned into one-degree cells and UTC hours. A single aircraft counts once in
each cell/hour; low or unavailable accuracy takes precedence if it also reports
good accuracy in that cell/hour. Counts are aircraft-cell-hour observations,
not unique aircraft across the day or independent corroborating sources.

The current assumption treats integer NACp 0 to 5 as low/unavailable accuracy,
and 6 to 11 as good. Missing, malformed, fractional or out-of-range values are
ignored. Reports without an aware observation timestamp, future reports, and
reports already older than 24 hours at admission are ignored. Repeated sampling
uses observation time, so cached aircraft positions cannot become new hourly
observations just because another polling cycle starts.

The adjusted share is `max(0, 100 * (bad - 1) / (good + bad))`, rounded to one
decimal place. Amber begins at 2%; red is above 10%. At least five observations
are required. Operators can choose red only and increase the minimum to 10, 25
or 50. Green cells are not drawn.

Buckets retain approximately 24 hours, including the oldest overlapping hour,
so retention can approach 25 hours. This preserves late-hour observations until
their whole bucket expires. Sampling and reads both prune expired buckets. The
latest-observation timestamp only advances for valid retained reports. Empty
collection cycles leave that timestamp unchanged.

These cells do not confirm deliberate jamming or spoofing, identify a GNSS
constellation, locate transmitters or describe measured interference boundaries.
Receiver coverage varies and a blank area is not evidence of no interference.
GNSS selection works independently of the Flights switch, country selection and
general event filters. Cell selection highlights the polygon; closing its
details removes that highlight.

Primary references reviewed on 9 September 2026:

- [GPSJam FAQ](https://gpsjam.org/faq) explains the limits of navigation-accuracy
  proxies and the adjusted-share convention. ASE uses different spatial and
  counting units; this is not a claim of methodological or dataset equivalence.
- [EASA GNSS outages and alterations](https://www.easa.europa.eu/en/domains/air-operations/global-navigation-satellite-system-outages-and-alterations)
  distinguishes jamming and spoofing and provides official guidance. The panel
  links to this resource; the app does not ingest its affected-area list.

## Efficiency and failure handling

- At most 250,000 aircraft-cell-hour assignments are retained in the GNSS
  aggregate. New assignments beyond the limit are omitted; existing assignments
  can still be updated. The API exposes `limited`, and the panel discloses that
  counts and shares are partial until affected hourly buckets expire.
- No new polling provider, persistent raw-event archive or dependency was added.
- The browser requests GNSS only while the layer is enabled and the page is
  visible. Polling occurs every five minutes with one pending request at a time.
  Disabling, hiding, unmounting or refreshing aborts the previous request.
- The UI records the last successful snapshot retrieval time separately from
  the latest aircraft observation time. A failed refresh retains the cached
  snapshot with an error message. After six minutes it is labelled out of date;
  after fifteen minutes its cells are hidden. The API lacks individual-cell
  timestamps, so cached cells are not claimed to remain inside a current window.
- Cell lists are paginated in groups of twenty. Map counts, list filters and
  displayed polygons share the same filtered data.

## Validation of the earlier GNSS implementation

Targeted backend regressions pass for timestamp validation, UTC hour boundaries,
duplicate polling, good/bad precedence, read-side expiry, capacity recovery and
authenticated API access. The final 17-test backend group achieved 94.20%
coverage across the changed domain and aviation application modules.

Frontend behaviour checks cover independent GNSS switching on both projections,
filtering, locating, highlighting and closing; panel ownership; keyboard time
selection; snapshot cancellation; slow requests; stale/error states; pagination;
and reduced graphics. The full frontend suite passed 1,365 tests across 279
files, with one opt-in stress benchmark skipped. Coverage was 95.37% statements,
90.38% branches, 93.67% functions and 96.70% lines. Eighteen final focused tests
also passed after clarifying the cache and dataset-timestamp labels.

ESLint, TypeScript, production build, changed-file formatting, Ruff, mypy,
architecture contracts and file-length checks passed. Scoped Bandit checks and
matching the proposed diff against two configured sensitive values found no
issues. Review checked validation, bounded aggregation and cancellation; API
regressions cover successful authorised access and rejection without a session.
The restarted local API exposed the new `limited` field; health and readiness
returned 200. No live GNSS coverage or browser frame-rate claim is made by these
checks.

Interactive browser/GPU inspection is still blocked by the administrator browser
policy established earlier in this task. Mock-engine integration tests do not
establish visual frame rates or driver stability. No production deployment,
provider purchase or external push is part of this change.

The repository-wide formatter currently reports three unchanged files:
`frontend/src/components/maps/MapImagePreview.tsx`,
`frontend/src/features/research/inputDeclarationCapacity.test.tsx` and
`frontend/src/lib/api/firmsConnection.ts`. All changed and new frontend files
pass formatting. The existing large vendor-chunk build warning remains.


## Follow-up: discoverability and useful location filters

The renamed Location quality panel explains four classes: source-reported exact,
approximate city/administrative positions, propagated satellite positions, and
records that cannot be plotted. Its selection now filters the actual event
markers in both projections. Counts describe records loaded within the other
active filters. A searchable, paginated list keeps records without coordinates
inspectable without inventing a point. These classes describe location metadata,
not source credibility, verified accuracy or estimated uncertainty radii.

Topics & time controls the shared live-event window and additional topic
switches. Category controls further narrow that event set. The Location quality
choice filters event markers, not independent GNSS cells, CCTV or infrastructure
catalogues. Restore All location qualities to remove this extra restriction. See
[map layers and planning tools](MAP_TOOLS_AND_LAYERS.md) for the accompanying
interaction, route-search, RF and OS map changes. Final verification for this
follow-up is recorded separately from the earlier milestone above.

## GPS interference under the Cyber control, 13 September 2026

The standalone GNSS switch left the layer rail. The Cyber control's panel now carries
two switches, "Cyber incidents" (the cyber event category) and "GPS interference" (the
aviation-derived interference cells), and a second tab holding the interference cell
list and filters unchanged. The layer itself, its data path and its doctrine notes are
the same; only the control that owns it moved. The user-facing name is "GPS
interference"; the code and API keep GNSS terms.

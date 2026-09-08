# Map interface and source improvements

8 September 2026. User direction: use OSIRIS as a reference for a cleaner,
minimalist map interface. Keep London, Kyiv, Moscow and Beijing as quiet clocks.
Every displayed data object must open useful details on both globe and flat map.
This extends the research expansion plan; it does not replace unfinished work.

## Composition and interaction

The map is the dominant workspace, with charcoal surfaces, compact controls and
one contextual inspector. Four small clocks provide orientation without a panel
heading, oversized numerals or a scrolling city rail. Dates and time zones remain
available to assistive technology and hover. Seasonal offsets use IANA zones.

Selection should reveal identity, source, observation time, freshness, geographic
precision, applicable measurements and an original-source link. Progressive
detail belongs in the inspector rather than permanently covering the map.
Clusters must expose their individual members as well as supporting zoom.
Drawing, measurement and report capture must not accidentally select objects.
Decorative basemaps and the day/night shading are context, not evidence objects.

## Source comparison

Read-only reference: [OSIRIS at the reviewed revision](https://github.com/simplifaisoul/osiris/tree/fac8d1b1dd3f9aab87bdeccdd04f05c25d5a3bb8).
Its demo could not be opened because browser policy verification was
unavailable. This review used repository source, not a live UI acceptance run.

| Family | Existing app and next useful work |
| --- | --- |
| Cameras | New capability: public traffic-camera catalogue, location markers and selected-camera previews. |
| Aviation | ADSB.lol and watched areas already exist. Improve current-position age, aircraft details and optional OpenSky coverage. |
| Maritime | Fintraffic regional AIS already exists. Add optional AISStream for broader coverage; distinguish moving vessels from static ports and chokepoints. |
| Hazards | USGS, EMSC, GDACS, EONET, FIRMS and weather feeds largely overlap. Prioritise clearer filtering and selected-event details. |
| Space | Existing CelesTrak propagation, NOAA and Copernicus research overlap. Label predicted orbit positions separately from observations and available imagery. |
| News/conflict | Consider broadcaster links and permitted public-channel collection; keep approximate keyword-derived locations and curated conflict context explicit. |
| Cyber | Existing CISA, outage and domain-research capabilities overlap. A map redesign does not introduce arbitrary-target scanning. |
| Crypto/designations | Potential focused research module, with candidate matching, source dates and corroboration rather than definitive identity badges. |
| Infrastructure/air quality | Add only verified catalogues relevant to research questions, with static/dynamic status and source attribution. |

OSIRIS's maritime code includes an AISStream connection when configured; without
the key it supplies static maritime context. Its named satellite-AIS fallback is
an empty implementation. Camera counts include snapshots, embeds, external links
and unavailable sources, not just verified live videos. Software licensing does
not grant rights to every downstream feed.

## Camera implementation sequence

1. Add a bounded server-side camera catalogue with stable provider IDs,
   coordinates, provider attribution, metadata freshness and playback kind
   (`snapshot`, `stream`, `external`). Cameras are facilities, not transient
   incident events; keep their catalogue separate from the public event store.
2. Start with official TfL, Hong Kong Transport Department and Fintraffic
   catalogues. Validate permitted usage, image hosts and actual availability.
   No discovery of private cameras or scanning for exposed feeds.
3. Render camera symbols and clusters in the shared map/globe layer registry.
   Selecting one uses the same inspector pattern. Fetch an image only when
   selected, with bounded caching, cancellation and explicit stale/offline state.
4. Preserve aspect ratio and attribution. Do not autoplay multiple streams.
   Display capture time when supplied, never substitute metadata retrieval time.
   Unknown capture age must be labelled unknown. External-only feeds get a link.
5. Add explicit research handoff and deliberate evidence capture where permitted,
   freezing bytes/hash/provider/time under the existing private retention policy.
   A changing image URL alone is not reproducible evidence.

Provider rules to implement and verify:

- [TfL](https://tfl.gov.uk/info-for/open-data-users/our-open-data): approximately
  two-minute refresh, maximum fifteen-minute image display age and no cropping.
- [Hong Kong](https://data.gov.hk/en-data/dataset/hk-td-tis_2-traffic-snapshot-images):
  approximately two-minute snapshots, including a provider No Service image.
- [Fintraffic](https://www.digitraffic.fi/en/road-traffic/): approximately ten-minute
  images, operational status and documented image history.
- [AISStream](https://aisstream.io/documentation): backend credential/connection,
  reconnect/backoff and freshness are required; no durable replay or SLA assumed.
- [OpenSky](https://openskynetwork.github.io/opensky-api/rest.html): credential and
  quota-dependent coverage must be disclosed.
- [adsb.fi](https://github.com/adsbfi/opendata): personal/non-commercial terms,
  one request/second and current v3 radius API mean it is not a drop-in provider
  for an organisational deployment.

## Acceptance

- [x] Four requested clocks only, desktop/mobile fit and seasonal-offset checks.
  Seven focused clock/control cases passed. Actual component screenshots were
  inspected at 390 × 844 and 1440 × 900 using the project's Tailwind styles.
- [x] Clickable event markers, clusters and interference cells on both projections.
- [x] Report-map overlays, AOIs and imagery footprints reveal attributed details.
- [x] Keyboard-accessible inspector controls and useful empty/stale states.
- No synthetic transport positions, invented camera timestamps or unverified
  live-video claims. Camera/provider additions remain pending implementation.
- Real GPU projection checks and camera playback/provider acceptance are separate
  from mocked layer tests and isolated clock-component visual checks.

### Completed map interaction verification

Event overlap selection includes obscured cluster members. Interference details
refresh with the selected cell and label the provider's adjusted percentage.
Report overlays and imagery footprints have attributed details. Drawing,
measurement and capture retain their selection guards.

Real shared-renderer checks on local fixtures passed in globe and Mercator:
point overlaps, interference cells, AOI geometry, aircraft, vessels and thermal
icons. Aircraft and vessel headings were visually checked north/east. Far-side
globe icons remain hidden. SVG intrinsic dimensions and globe-specific icon
orientation were repaired after real browser failures. No global culling override
was used. This checks the actual renderer and selection hook, not live provider
coverage or the complete authenticated dashboard.

The frontend suite passed 1,101 tests across 217 files before the final narrow
cluster/icon fixes (95.26% statements, 90.12% branches, 93.83% functions, 96.63%
lines). Final changes passed 39 focused tests, strict types, lint and production
build. Independent interaction review and actual GPU acceptance passed. No
camera catalogue or new transport-provider connection is enabled by this change.


## 8 September follow-up: compact controls

The user's screenshot exposed a persistent desktop control column that still
covered the working map. Replace it with narrow layer and tool rails. The initial
view must have no expanded map-style, measurement or source-information block.
Layer switches expose state and loaded counts; the complete settings remain
available on demand. Only one tool panel opens at once, with explicit close,
Escape and focus restoration. Non-modal panels preserve map gestures.

Direct controls cover flights, vessels, FIRMS, satellites, disasters, conflict,
news, day/night and GNSS. Tools cover map style, distance/area measurement,
observation filtering, country lookup, scope/settings and location precision.
Navigation adds bounded zoom, north-up reset, world reset and fullscreen where
supported. CCTV remains an explicitly unavailable entry until a camera catalogue
is implemented; no synthetic cameras or invented stream status are introduced.

Acceptance must cover the authenticated running app at desktop and narrow mobile
widths, including closing the measurement panel and continuing to pick points.


Compact-control regression run: 1,110 tests across 219 files passed, with 95.24%
statement, 90.07% branch, 93.76% function and 96.62% line coverage. Thresholds
were unchanged. Types, lint and production build passed. The subsequent
short-screen inspector/rail CSS adjustment has separate browser verification.
Authenticated Chromium checks cover the actual app at desktop/mobile sizes,
including live layer switches and geodesic measurement with its panel closed.
The run observed an existing WebGL front-face warning, also present in the
baseline; this control-layout work does not establish warning-free rendering.
No authentication, provider credentials, API contracts or database schema changed.


Final CSS acceptance passed at 1,024 × 600 and 390 × 600: event inspectors
and tool close buttons remain actionable; mobile inspection temporarily hides
rails and restores them on close. Vertical rail scrolling reaches lower controls
without horizontal scrollbars. The final CSS build and formatting passed.
Authenticated desktop/mobile screenshots were reviewed, with no remaining
blocking control-layout findings. New controls use static SVG paths and existing
authorised data/state; this milestone adds no remote input or privilege boundary.


8 September camera delivery: implemented an authenticated, bounded public camera
catalogue for TfL, Hong Kong Transport Department and Fintraffic. Added optional
camera markers, searchable provider filters, selection halos and requested
snapshot previews on globe/map. Actual provider images and both projection
clicks were verified. See CAMERA_FEEDS.md for checks, source terms, bounds and
remaining regions/evidence-capture work. This supersedes the earlier CCTV
unavailable notes above.

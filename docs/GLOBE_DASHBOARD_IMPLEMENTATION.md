# Globe dashboard, clocks and observation traffic

User-requested extension, 7 September 2026. Full scope remains open.

## Visual direction and current delivery

The globe remains the main canvas, with near-black surfaces, restrained cyan
controls, legible instruments and short entrance/hover transitions. Reduced-motion
preferences suppress these transitions. The clock rail shows London, Berlin,
Moscow, Tallinn, Beijing, Kyiv, Mumbai, Tokyo, Canberra and Washington DC. It uses
IANA timezones, 24-hour times and local dates, including daylight-saving changes.
All cities remain accessible by horizontal keyboard/touch scrolling on small screens.
Coordinate controls and the inspector sit above the rail.

Plane symbols already existed for selected ADS-B feeds and eight watched areas.
At low zoom, the new renderer keeps up to 250 sampled aircraft/vessel records out
of clusters, prioritising the selected record. Remaining traffic still contributes
to the normal cluster/singleton representation. Category filters continue to apply.
Boat symbols now require the explicit vessel_position subtype and use track_deg.
NAVAREA hazards and navigation warnings never become boat positions.

## Still required

- Browser visual acceptance on desktop/mobile, checking panel overlap, empty/error
  states, reduced motion and both projections with actual WebGL rendering.
- Further refinement of dashboard composition based on that visual inspection.
- Connect the implemented independent observation controls to provider health,
  acquisition-time and source-freshness disclosures when adapters are available.
- Actual vessel-position adapter, bounded collection/reconnection/retention,
  provider credential handling and permitted coverage/usage verification.
- Actual FIRMS adapter, explicit activation and separate thermal observation layer.
  Acquisition time is not ingestion time; thermal detections do not establish fires,
  explosions, attacks or other causes on their own.
- Free provider registration and email verification when browser access permits it.
  The user explicitly authorised free API setup and Gmail use for that purpose.
  No paid account, purchase or provider credential has been created.
- Shared globe/map selection, filtering, density and source/freshness tests for the
  new live integrations, followed by documented live smoke checks.

## Current external blocker and checks

Computer-use attempts to open the official NASA FIRMS API page and localhost both
failed before navigation because the browser could not verify its admin-enforced
security policy. No browser-security bypass or alternate signup route was used.
Gmail has not been accessed, since registration could not begin. Provider terms,
limits and availability have not been freshly verified. Existing documentation
describes candidates, not completed FIRMS/AISStream integrations.

All 112 globe-feature tests in 20 files passed, including clock seasonal offsets
and the vessel-versus-warning distinction. Scoped ESLint and frontend type checks
passed. Production build passed with the existing chunk-size advisory. No screenshot or real GPU acceptance
is claimed. Changes remain in the working tree alongside the ongoing full plan.


### Independent observation display controls

Added aircraft, vessel-position and FIRMS thermal switches with counts under the
current country/time scope and an explicit category-hidden notice. Switching off
FIRMS leaves other disaster records; switching off vessels leaves maritime
warnings. Geographic precision lists use the same observation filter. The ticker
continues showing scoped source reporting. Controls explicitly disclose that vessel
and FIRMS connections are not configured. They do not activate providers.

Three focused overlay tests passed, including selected traffic beyond the first
250 records and category hiding. Type checks and scoped ESLint passed. The preceding
full frontend run failed only its branch gate at 89.98%; the threshold remains 90%.
That run was superseded by the successful full rerun recorded below.


### Dashboard review repairs and integration checks

The full frontend overlay run passed 813 tests in 147 files: 95.41% statements,
90.06% branches, 94.12% functions and 96.62% lines. The existing coverage gate is
unchanged. Subsequent review repairs reserve a bottom attribution gutter, keep
expanded attribution above instruments and use a transparent boat-deck cutout
for the icon mask. World clocks now subscribe at minute boundaries rather than
using the relative-time bucket. All 116 globe tests passed after these repairs.
Type checks and production build passed; a test-only floating-expression lint
issue was repaired and scoped ESLint then passed. Browser/GPU acceptance and
actual vessel/FIRMS onboarding are still outstanding.

The official FIRMS registration page was retried using computer use. The same
admin-enforced browser policy verification failure prevented navigation. No
account, API key or Gmail verification was completed. The remaining connection
work cannot be described as live merely because its display switches exist.

Final frontend verification passed 814 tests in 148 files, with 95.42% statement,
90.05% branch, 94.14% function and 96.63% line coverage. The mobile controls portal
now shares the dashboard palette even though it is mounted outside the globe
container. Browser visual acceptance remains outstanding.

### Spherical clustering and current integration result

Low-zoom groups now use quantised unit vectors and vector-mean centres. Nearby
records across the date line and around either pole no longer produce a false
central longitude. Categories remain separate and all located input records remain
represented. This is bounded grid aggregation, not radius-neighbour clustering;
points on bin boundaries may still form separate groups. Original coordinates are
unchanged. Nine regressions cover the seam, poles, counts and invalid widths.

All 125 globe tests in 23 files passed. The final frontend suite passed 852 tests
in 153 files, with 95.48% statements, 90.18% branches, 94.19% functions and 96.65%
lines. Type checks, scoped ESLint and production build passed, retaining the existing
bundle-size advisory. These results do not establish current WebGL visual parity.
Free API registration remains blocked by the browser policy-verification failure.

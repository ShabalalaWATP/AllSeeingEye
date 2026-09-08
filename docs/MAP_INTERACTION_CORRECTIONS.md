# Map interaction corrections

8 September 2026, following operator feedback on labels, styles, grid references
and event selection.

## Behaviour

- One sidebar Map destination preserves the chosen projection. The map's own
  Globe and Map buttons and keyboard shortcuts remain available.
- Aircraft, vessel and CCTV control icons use recognisable shapes. Hover and
  keyboard labels render outside the scrolling rails. Map style retains a visible
  text label and opens its choices directly.
- Approximate location circles have a subtle pickable interior. Overlapping items
  open a chooser; the clicked location and chosen event receive a white selection
  halo. Closing details clears the halo. Hidden events are not highlighted.
- Selection remains visible for an event represented by a low-zoom cluster.
- The existing globe front-face string reached a legacy WebGL call as an invalid
  enum. Numeric WebGL constants now preserve icon winding without that warning,
  while retaining headings and far-side culling.

## What conflict markers mean

The internal conflict category is displayed as **Conflict & unrest**. The current
GDELT adapter includes CAMEO roots 14 (protest), 15 (force posture), 17 (coercion),
18 (assault), 19 (fighting) and 20 (mass violence). These are automated news
classifications, not independently verified armed conflicts. The inspector now
explains this explicitly. Approximate circles mark reference locations, not
incident boundaries or an asserted area of fighting.

This matches the broad scope and error caveat in [GDELT's own conflict dashboard
description](https://gdeltproject.org/globaldashboard/). Original subtype, source,
classification rationale and geographic precision remain available.

## British National Grid

The previous app only had WGS84 cursor coordinates and optional OS raster styles;
there was no BNG implementation. The new grid is separate from those basemaps and
does not require an OS tile key. Enable British National Grid and choose Locate
Great Britain, or zoom to the region. It shows 100 km lines from zoom 5 and 10 km
lines from zoom 8, bounded to 202 lines and 18,602 vertices. Lines are not pickable
and do not intercept event selection. The cursor reports eastings/northings
rounded to 10 m inside the supported extent.

The pinned MIT [Proj4js](https://proj4js.org/) dependency uses the documented
[Ordnance Survey Helmert alternative](https://github.com/OrdnanceSurvey/os-transform).
OSTN15 correction is absent, so this is approximate rather than survey-grade.
The extent includes surrounding water; it is not a political boundary mask.
Independent OS example coordinates and bounds are tested. The disabled grid and
unchanged spacing preserve layer identity to avoid rebuilding overlays while
panning or making small zoom changes.

## Verification scope

Actual authenticated Chromium checks cover labelled styles, sidebar navigation,
visible BNG lines and coordinates, red-circle centre selection, overlap choices,
and event highlight/dismissal. Mobile checks cover 390 x 844. Controlled local
renderer fixtures cover aircraft, vessel and thermal clicks in both projections,
near/far culling and north/east headings. No synthetic fixture data is published
to the app or its event service.

The local fixture's favicon 404 and initial style-replacement warning are separate
from product behaviour. The actual app's Streets style emitted a missing
circle-11 sprite warning; the prior invalid front-face warning did not recur.
No backend schema, account permissions, source admission or credentials changed.


Final regression run passed 1,129 tests across 223 files: 95.22% statements,
90.08% branches, 93.58% functions and 96.57% lines, with unchanged thresholds.
The earlier run exposed an outdated sidebar button assertion, corrected to the
single Map link. A grid-disabled layer-identity regression was repaired against
the existing performance test. Final combined types, lint and build passed.
Subsequent grid-icon and mobile coordinate-clearance adjustments passed 12
focused tests, a production build and actual browser clearance checks.
Production dependency audit reported no known vulnerabilities.

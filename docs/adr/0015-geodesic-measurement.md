# 0015: WGS84 map measurements

Accepted for local implementation, 7 September 2026.

The map plan requires geodesic distance and area without a custom formula suite.
The existing frontend lockfile had no geodesic measurement dependency. Add the
official `geographiclib-geodesic` package, pinned to 2.2.0. Its repository and
installed metadata identify Charles Karney's GeographicLib JavaScript routines,
MIT licence, included TypeScript declarations and no runtime dependencies.

Sources checked:
- https://github.com/geographiclib/geographiclib-js
- https://geographiclib.sourceforge.io/html/js/
- Installed package metadata and declarations, matched to the pinned lockfile.

Use the WGS84 ellipsoid for numeric path distance, polygon perimeter and absolute
signed net area. A polygon closes its final point to the first. Self-intersections
cancel algebraically; the result is bounded to the smaller half-earth region.
It is not an area measure for an intended greater-than-hemisphere interior.
Terrain, altitude and source-coordinate uncertainty are not incorporated.

Retain at most 32 local vertices. Render 64 geodesic intervals per edge, at most
2,080 sampled positions, using non-pickable paths and vertex markers. Display
sampling is not the numeric measurement algorithm. Flat maps omit portions beyond
Mercator's latitude limit, preserving the original vertices and numeric result.
Actual GPU seam/polar and close-zoom drawing fidelity still require visual checks.

Dashboard measurements are page-local UI state, not evidence or observations.
They never enter shared events or provider requests. Account or workspace-access
changes clear both vertices and coordinate-entry drafts.
Country/ticker navigation remains available while measuring to reach distant
points; marker/cluster picking does not open an inspector or change camera focus.
Typed entry works without WebGL; map picking requires a supported map.

## Saved report-map extension

Report maps now share the same panel and rendering functions. Their optional
measurement state retains the original ordered coordinate pairs, distance/area
mode and `wgs84-geographiclib-2.2.0-v1` method. Results are derived in the client,
never accepted from a submitted total. The pinned implementation and regression
fixtures must remain compatible with this identifier; a future algorithm change
needs explicit method dispatch or a new version with a migration decision.

Empty and incomplete sketches are valid drafts, including their selected mode.
Clear removes the measurement entirely. At most 32 finite WGS84 pairs are allowed;
unknown methods, extra ordinates and submitted result fields are rejected. No
rounding, point reordering or closing vertex is added to retained coordinates.

Saving uses the existing report-version ownership, team scope, revision history,
integrity hash and byte quota. The optional field is omitted from canonical JSON
when absent or null, preserving legacy revision hashes without a database migration.
It remains an operator measurement separate from evidence and research AOI.
Measurement and AOI picking are mutually exclusive. Closing the renderer stops
measurement picking; losing authority unmounts the private map and panel.

This extension does not provide a rendered map-image export or real GPU acceptance.

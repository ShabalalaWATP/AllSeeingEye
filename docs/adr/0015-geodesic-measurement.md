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

Measurements are page-local UI state, not evidence or observations. They never
enter shared events, provider requests, report storage or exports. Account or
workspace-access changes clear both vertices and coordinate-entry drafts.
Country/ticker navigation remains available while measuring to reach distant
points; marker/cluster picking does not open an inspector or change camera focus.
Typed entry works without WebGL; map picking requires a supported map.

# ADR 0001: Globe and map engine

Status: Accepted (proposed 2 September 2026, accepted by Alex 3 September 2026)

## Context

The primary view is a 3D globe. Users must be able to switch to a 2D map with Ordnance Survey (Great Britain), satellite and hybrid base layers, and the app must render tens of thousands of moving or static points (aircraft, vessels, fire hotspots, news items) with filtering by nation and time. The project is a hobby product: free tooling, a small bundle, and a maintainable React integration matter more than photogrammetry or terrain fidelity.

## Options

1. **MapLibre GL JS 6 with the globe projection, plus deck.gl 9.3 for data layers.** Globe mode arrived in v5 (December 2024) and v6 (July 2026) requires WebGL2 and ships ESM only. One engine renders both the globe and the 2D map: the `globe` projection preset flattens to Mercator between zoom 10 and 12, so "globe versus map" is a projection toggle rather than two libraries. Raster tile sources (OS Maps, satellite mosaics, NASA GIBS) and vector tiles (dark base map) work in both projections, as do terrain and heat maps. deck.gl has supported the MapLibre globe since 9.1 and attaches through `MapboxOverlay` to render large point, icon, arc, path and H3 layers on the GPU. BSD licence, no token.
2. **CesiumJS with Resium.** True 3D with terrain, 3D Tiles and time-dynamic entities, a mature choice for flight and satellite visualisation. The minified core alone is about 6 MB, the API is imperative and fights React, 2D cartography is weaker, and while an ion token is only needed for ion-hosted assets, the ecosystem assumes it. Resium is maintained (monthly releases).
3. **globe.gl / react-globe.gl.** Beautiful Three.js globe with arcs and points, very quick to start. No tile base maps, no street-level zoom, no OS Maps, so a second map library would be needed for map mode, doubling the layer code.

## Decision

Option 1. Wrap the engine behind a small `MapEngine` interface and describe every data layer declaratively in a layer registry, so the choice can be revisited if a hard requirement for terrain or true 3D appears.

## Consequences

- One rendering code path for globe and map; the base-layer switcher is a style swap.
- WebGL2 is mandatory, which every current desktop and mobile browser provides.
- OS Maps tiles are proxied through the backend to keep the key server-side and to respect the 600 transactions per minute limit; the free plan covers Road, Outdoor and Light at zooms 7 to 16, Great Britain only.
- Hybrid view is composed from a satellite raster layer plus a labels-only vector layer (Protomaps), because MapLibre has no built-in labels overlay.
- Esri World Imagery carries a sunset risk (legacy raster basemaps retiring in phases from October 2026), so EOX Sentinel-2 cloudless and NASA GIBS are the default satellite sources.
- 3D terrain is possible with free DEM tiles (Mapterhorn, AWS Terrarium) but is not a phase-1 feature.
- deck.gl and MapLibre versions must be kept in step; pin both.

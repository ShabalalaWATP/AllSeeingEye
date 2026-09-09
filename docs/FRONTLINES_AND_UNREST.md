# Conflict globe markers, unrest and frontline sources

9 September 2026.

## Globe repair

Conflict regional icons and selected labels omitted the tangent orientation,
clockwise WebGL winding and local 180-degree correction used by existing globe
aircraft and camera symbols. The globe renderer culls the resulting quads.
The regional icon and text layers now follow the established projection handling;
back-face culling remains enabled to hide objects on the far side of the Earth.

The renderer also changes to a Mercator surface above zoom 12, even while the
Globe tab remains selected. A small render-view subscription now tracks that
threshold separately from coarse clustering bands. Symbol orientation changes
at the threshold without forcing layer rebuilds for every pan or fractional zoom.
SVG winding remains explicit because the globe renderer retains its culling state
at close zoom. Camera and infrastructure symbols share the effective projection.

A dark badge improves contrast against imagery. War regions use crossed swords;
tension areas use an amber warning symbol. Selected regions retain their halo,
context outline and click-through inspector, with a larger selected glyph.
Regional markers remain approximate research locators, not incident coordinates
or territorial boundaries. The category rail uses the same war symbol.

## Report types and symbols

The Conflict reports panel separates Protests / demonstrations from Riots /
violent demonstrations and Unrest (type unspecified). A demonstration does not
establish violence by protesters, and unrest does not establish armed conflict.

| Type | Symbol | Meaning |
| --- | --- | --- |
| Armed clashes | Red crossed swords | Source/screening type indicates armed clashes |
| Organised violence | Rose shield with warning | Broad armed-violence type, without a more precise supported subtype |
| Strikes and explosions | Orange burst | Source-coded strikes/explosions; retains original details |
| Violence against civilians | Pink person/shield | Within or outside a war |
| Protests / demonstrations | Blue placard | No assumption of protester violence; can include intervention against protesters |
| Riots / violent demonstrations | Amber triangle/bolt | Explicit source type, not inferred from headline words |
| Unrest (type unspecified) | Purple question symbol | Broad screening result without supported protest/riot specificity |
| Military activity | Green flag | Activity is not necessarily violence |
| Other reported incidents | Grey diamond | No more specific supported classification |

The same symbol catalogue supplies the report filters, inspector and event icons.
Approximate event points retain their precision rings. Clusters remain aggregates;
zooming or inspecting members reveals individual types. Existing screening,
historical and unreviewed-report exclusions are retained.

ACLED already supplies distinct protest and riot types. Broad LLM `civil_unrest`
does not establish a riot: compatible explicit provider types are retained,
otherwise the report remains unspecified unrest. Source attributes are not changed.
For GDELT only, the exact CAMEO codes 145 and 1451 through 1454 refine the broad
protest subtype to a machine-coded riot/violent demonstration. These codes are
defined in the [GDELT-hosted CAMEO codebook](https://data.gdeltproject.org/documentation/CAMEO.Manual.1.1b3.pdf).
The existing source-text screening gate still applies; the code alone does not
make an unreviewed report eligible for display or independently verify violence.
No new source, LLM call or classifier prompt is introduced by these display changes.

## Frontlines: verified options and access limits

The map's Conflict reports panel now includes **Frontlines**, an access directory
with official source and access links. It explicitly says no boundary feed is
connected. Opening it starts no provider requests and enables no map layer.
The app does not present a non-functional visibility switch as an integration.

### ISW / Critical Threats

The official [Ukraine StoryMap](https://storymaps.arcgis.com/stories/36a7f6a6f5a9448496de641cf64bd375)
links through a 3D viewer and web scene to
[control-of-terrain polygons](https://services5.arcgis.com/SaBe5HMtmnbqSWlu/arcgis/rest/services/VIEW_RussiaCoTinUkraine_V3/FeatureServer/49).
The [source item](https://www.arcgis.com/home/item.html?id=cd40e3953c4c47ddb17053459a411e2b)
is owned by `gbarros_understandingwar` and requires written consent for geodata use.
Its [fair-use and attribution policy](https://understandingwar.org/fair-use-and-attribution-policy/)
also requires permission for incorporation into other mapping platforms.
JSON/GeoJSON query support does not establish permission to copy or redistribute it.

### DeepState

The [official licence](https://deepstatemap.live/license.html), revised 3 September
2025, controls API use and prohibits unauthorised proxying/redistribution.
Commercial use requires prior agreement; specific charitable/volunteer and Ukraine
defence uses have different terms. The operator's intended deployment and actual
permission must be established through the [API access process](https://api.deepstatemap.live/request).

OSIRIS's [frontlines route](https://github.com/simplifaisoul/osiris/blob/11ecf488253c202714ab11709750b651c765e07b/src/app/api/frontlines/route.ts)
fetches DeepState history directly and adds a download timestamp with a 30-minute
cache. ASE leaves this connection disabled until reuse rights are confirmed and
keeps download time separate from the age of the underlying assessment.

### UN OCHA Ukraine

The [hosted frontline layer](https://gis.unocha.org/server/rest/services/Hosted/UKR_Front_Line/FeatureServer/0)
supports JSON/GeoJSON lines and describes weekly updates. The ten features checked
during this research were dated **2 September 2026**. It derives from ISW/CTP.
The [item metadata](https://gis.unocha.org/portal/sharing/rest/content/items/ff87995e5ccb4c6bb77f116b22e2ff45?f=pjson)
limits intended use to humanitarian purposes. This is not permission for a general
OSINT product. A separate older July layer surfaced in search; it was not substituted
for the current hosted series. No boundary geometry is embedded in this app.

### Liveuamap

The [provider's API example](https://github.com/liveuamap/liveuamap.consolecsharp.api)
documents a keyed API with events and areas. It is old. Current price, terms and
entitlement to territorial boundaries could not be verified because current site
pages returned 403. The UI therefore says provider access and current terms are
required, not that worldwide live frontlines are available or free.

### War Mapper and other prominent wars

[War Mapper](https://warmapper.org/about) describes active Ukraine and Sahel coverage.
Its Syria, Gaza, Armenia/Azerbaijan and Sudan series are labelled historical.
Published maps/charts/statistics allow reuse with attribution and a link, while
access to the underlying data requires contact. No public geometry API was verified.

This search did not establish an unrestricted automatic boundary provider for every
prominent war. Incident APIs, including ACLED, are useful for protests, riots and
political violence but do not supply territorial control merely because events are
geolocated. ASE must not manufacture a frontline by joining incident locations.

## Required contract for a future authorised connection

1. Confirm provider rights, authentication, actual regions and supported geometry.
2. Add a fixed provider adapter behind the existing outbound guard; no arbitrary URL
   proxy, private-network access or credentials in the browser.
3. Bound response bytes, feature/vertex counts, cache size and request frequency.
   Fetch only when requested, reuse a shared cached snapshot and back off on failure.
4. Preserve publisher IDs, assessed/claimed/contested classes, assessment date,
   download time and attribution separately. Missing dates remain unknown.
5. Put provider and geography controls under Frontlines, off by default. Show stale,
   unavailable and incomplete coverage states, not silent substitution by another source.
6. Use the existing shared renderer for both projections. Selectable lines/polygons
   must expose provenance; closing details clears selection.
7. Keep disputed-source geometries separate and distinguish apparent changes caused
   by provider revisions from newly observed territorial changes.

No provider agreement, paid subscription, access request or credential has been
created or sent. The operator was asked whether authorised access already exists.
Integration of updating geometry remains dependent on resolving that access.

## Validation scope

Projection and classification regression tests cover these changes; final test
counts and broader checks are recorded in the development story. No current browser
or GPU acceptance is claimed because the existing browser policy remains unresolved.
No backend API, database, dependency or collection-loop change is required here.

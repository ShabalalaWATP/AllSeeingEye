# Public map infrastructure

The optional undersea-cable and ground-station layers use packaged public snapshots.
They load through the authenticated `/api/map-infrastructure` endpoint. They are
independent of the rolling live-event window. Both layers start switched off.

## Cable data and licence

The 8 September 2026 snapshot contains 1,999 OpenStreetMap cable **segments**, not
1,999 complete named cable systems. It is a bounded sample of the first 2,000 ways
returned by Overpass, so geographical coverage is incomplete and uneven. Ferry and
mooring cables were excluded. Optical, power and unspecified submarine cables may
remain. Do not infer service status, ownership or exact engineering routes.

Source query, submitted to `https://overpass-api.de/api/interpreter`:

```overpass
[out:json][timeout:40];way["seamark:type"="cable_submarine"];out geom 2000;
```

The source timestamp was `2026-09-08T12:38:11Z`. Coordinates are rounded to five
decimal places. Consecutive duplicate points are removed; paths over 512 vertices
are evenly sampled with both endpoints retained. The packaged snapshot contains
33,357 vertices. Each segment links to its original OSM way.

Data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
available under the Open Database Licence. The packaged derived cable database
remains available under ODbL, independently of the application source licence.
Preserve this attribution, source links and licence notice when redistributing it.
The source tag is documented in the
[OSM marine tagging reference](https://wiki.openstreetmap.org/wiki/Tag:seamark:type%3Dcable_submarine).

OSIRIS provided interface inspiration. Its TeleGeography cable data was not copied:
[TeleGeography's reuse policy](https://www2.telegeography.com/cite-telegeography-map)
restricts the underlying database separately from map-image reuse.

## Ground stations

The 25 entries link to public operator descriptions. See
[GROUND_STATIONS.md](GROUND_STATIONS.md) for the station inventory and coordinate
method. These markers identify approximate sites or localities, not antenna
positions. Some locality markers are several kilometres from the actual station.
They do not imply current operational activity or access to station telemetry.

## Boundaries

No user URL is fetched and no map action contacts a station or cable operator.
The server reads fixed packaged resources only. API and client validation bound
the number of features and vertices. Snapshot dates and provenance accompany the
data; there is no automatic assertion of freshness.

## Ground stations from Wikidata and data centres from OpenStreetMap, 13 September 2026

Two operator-run commands extend the packaged snapshot:

- `uv run ase import-ground-stations` merges Wikidata items that are ground stations or
  teleports with a recorded coordinate, an ISO country and no dissolution date, behind
  the 25 curated entries (sites within 0.05° of a curated one are dropped). Each carries
  a Wikipedia or Wikidata source link, a website where recorded, and a note that the
  position is an approximate site, not an antenna or a statement of current use. The
  snapshot now holds 106 stations. Sources tried and left for later: OpenStreetMap
  `man_made=ground_station` (six features worldwide), named `satellite_dish` features
  (125, mostly single dishes), and national earth-station licence lists, which need a
  per-country parser.
- `uv run ase import-data-centres` queries Overpass for `telecom=data_center` features
  with a name and writes `data_centres.json` (3,600 of roughly 3,614 named features,
  ODbL, attributed). Country is resolved from the mapped position with the packaged
  Natural Earth index, so 63 sites near coasts or borders carry no country. The panel
  lists them as a fourth layer with an operator website link in the inspector.

Neither dataset states capacity, tenants or operational status; the inspector says so.

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

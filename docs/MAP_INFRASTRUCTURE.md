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

## Owner, purpose and links on existing records, 13 September 2026

`uv run ase import-infrastructure-notes` adds fields without moving or removing a record:

- Cables: the OpenStreetMap way tags for the 429 named segments
  (operator, owner, description, website, `wikipedia`, `wikidata`) and, where a way names
  a Wikidata item, that item's owners, description, website, article and inception.
  376 segments gained at least one field. The 1,570 unnamed
  segments carry no tags to enrich.
- Nuclear plants: a Wikidata name search per WRI record, accepted only when the hit reads
  as a nuclear plant and sits within 0.5° of the packaged point; 64
  of 195 matched and gained owner, description, website and article links.
- Ground stations: the same search for the curated entries; 84
  of 106 now carry an article or Wikidata link.

The inspector shows one facts block for every kind: operator, owner, country, inception,
significance, description, links and the precision caveat. Enrichment is public-record
background, not verification of who runs a site today.

## Oil and gas facilities and semiconductor sites, 13 September 2026

Two researched layers join the infrastructure panel. Each merges a curated list of key
sites, resolved through Wikidata's entity API (search, then coordinates, operator,
owner, description, website and article), with OpenStreetMap breadth. Curated sites
carry a written significance and are drawn larger; sites whose Wikidata item has no
coordinate are placed at the named city and say so (`precision: city`).

- Oil and gas (`ase import-energy-sites`): 74 curated sites from
  `energy_key_sites.json` (Gulf refineries and terminals such as Ras Tanura, Abqaiq,
  Ras Laffan, Kharg Island and Basra; Russian export ports and refineries such as
  Primorsk, Novorossiysk, Kozmino, Sabetta and Omsk; UK refineries and gas terminals
  such as Fawley, Grangemouth, St Fergus and Bacton; US refineries, Cushing, Sabine Pass
  and LOOP; Rotterdam, Jamnagar, Zhenhai, the Caspian fields and the BTC, Druzhba,
  Nord Stream and Trans-Alaska pipelines) plus OpenStreetMap refineries
  (`industrial=refinery`), named offshore platforms and operator-tagged oil facilities,
  2789 sites in total, 18 at city precision.
  Unresolved seeds: Yanbu Refinery, East–West Pipeline, Sidra Libya.
- Semiconductors (`ase import-semiconductor-sites`): 60 curated sites
  from `semiconductor_key_sites.json` covering TSMC (Hsinchu, Tainan, Taichung,
  Kaohsiung, Arizona, Kumamoto, Dresden), Samsung, SK hynix, Intel, Micron,
  GlobalFoundries, UMC, SMIC, YMTC, CXMT, Hua Hong, Texas Instruments, Infineon,
  STMicroelectronics, Bosch, Rapidus, Kioxia, Renesas, Sony, Wolfspeed, Tower, Nexperia,
  the equipment chokepoints (ASML, Zeiss SMT, Tokyo Electron, Applied Materials, Lam),
  Shin-Etsu wafers and the ASE and Amkor packaging plants, plus OpenStreetMap features
  tagged as semiconductor works: 98 sites, 47 at city
  precision because most fab items on Wikidata are company records without a coordinate.

Sources considered and not used: Wikidata's SPARQL endpoint (returned 502 and
disconnects during this work, so the entity API is used instead); Global Energy
Monitor's oil and gas trackers (CC BY 4.0 but behind a download form, a candidate for a
licensed import later); OpenStreetMap `man_made=petroleum_well` and pipelines (too many
features to package usefully). Site records state that output, ownership and current
operation are not verified.

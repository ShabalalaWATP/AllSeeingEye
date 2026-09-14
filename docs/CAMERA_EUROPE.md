# European public camera integration

Reference: [OSIRIS CCTV modules at fac8d1b](https://github.com/simplifaisoul/osiris/tree/fac8d1b/src/app/api/cctv).
The country catalogue modules retain the reference MIT copyright and permission
notice. Camera imagery remains subject to each provider's terms, independently
of the code licence. Catalogue coordinates are preserved, not newly geocoded.
Curated positions are marked approximate. A listed stream is not an assertion
that its content is currently broadcasting or that its location is verified.

## Coverage and observed availability, 8 September 2026

| Source | Implementation and check |
| --- | --- |
| Austria / ASFINAG | Fixed official index adapter. Unauthenticated request returned 401. The reference's embedded Basic credentials were not copied. Provider remains unavailable pending legitimate authorised configuration. |
| Netherlands / Rijkswaterstaat | Official index returned 26 records. The current URL needs a trailing slash. Public player links retained externally: both direct snapshots and the sampled player require origin authorisation. No Referer spoofing or proxy bypass. |
| Iceland / Vegagerðin | Official index yielded 500 valid cameras. Sample JPEG returned successfully. |
| Spain / DGT | Official index yielded 1,913 valid cameras from 1,918 rows. Sample JPEG returned successfully from etraffic.dgt.es. |
| Bulgaria | Three curated records. UAB and Chavo returned images; Smart Burgas returned an HLS manifest. The reference's generated Bulgarian catalogue is empty. |
| Greece | Two Attiki Odos IPCamLive public player embeds. Sample player document returned successfully; this does not prove video playback. |
| Serbia | Two records. Belgrade returned a JPEG and AMSS Gradina returned an HLS manifest. |
| North Macedonia | Two Neotel border streams. Sample returned an HLS manifest. |
| Turkey | Explicitly unavailable. OSIRIS itself removed its entries because embedding was restricted. No invented replacement coordinates. |
| Romania | One curated record, sample JPEG returned successfully. |
| Italy | 16 Skyline provider links. Poster JPEGs deliberately omitted because catalogue posters are not reliably fresh. |
| Czechia | Three curated YouTube embeds. Player document response is not independent verification of a live broadcast. |
| Slovakia | Two curated YouTube embeds, same limitation. |
| Germany | Two curated YouTube embeds, same limitation. |
| France | 40 curated entries: YouTube embeds, Skyline links and external APRR/AREA map links. Highway markers are reference approximate locations, not independently surveyed camera installations. |
| Spain curated | 53 entries: YouTube embeds and Skyline provider links, separate from the DGT source. |
| Poland | 73 curated entries, principally Nadmorski/TK Chopin HLS, plus YouTube and Słupsk MJPEG. Sample HLS failed local TLS certificate validation; verification was not disabled. Słupsk response exceeded the bounded 2 MiB probe, so content was not certified. |
| Switzerland | Six entries: five Skyline links plus CHUV snapshot/provider link. CHUV response exceeded the bounded probe; no image verification claim. |

Total additions observed: 2,644 catalogue records, comprising 2,439 official
index records and 205 curated records. These counts are not a count of working
live streams. Finland is covered by the existing Fintraffic source and is not
duplicated here.

## Boundaries and validation

Only four constant official index endpoints are fetched server-side. The
existing DNS-pinned HTTP client, certificate verification, byte cap and timeout
remain in force. No cookies, embedded credentials, stealth fetch, user URLs,
private cameras or open proxy were introduced. Upstream catalogues are capped
at 5,000 rows, IDs deduplicated, and invalid coordinates/media origins rejected.
Explicit media and frame host sets are exported for browser policy integration.
Sample HLS manifests referenced segments on the same origin, with no additional
segment domains observed.

31 deterministic tests cover catalogue coverage, provenance, invalid coordinates,
HTTPS/media origin constraints, malformed input, deduplication, row limits,
external-only RWS behaviour, fixed request arguments and retired providers.
Ruff formatting/checks and focused mypy apply to all European modules. Live
probes are separate from the deterministic test suite and do not establish
browser playback, freshness or all-camera availability.

## 14 September 2026: Britain, the Baltic states and Russia

Requested coverage: more UK providers with Scotland and the Cheltenham area in focus, plus
Russia, Estonia and Latvia. The search favoured official keyless indexes first and public
operator streams second; nothing private, credentialed or scraped from a login was added.

| Provider (id) | What it is | Observed on 14 September 2026 |
| --- | --- | --- |
| Traffic Scotland (`traffic-scotland`) | Transport Scotland's trunk-road cameras, fixed JSON index `https://www.traffic.gov.scot/tsis/cameras` with sid, title, position, road and region | 415 cameras parsed live. The operator serves each image only as a base64 JPEG inside a small HTML fragment (`/tsis/camerahtml?sid=N`), so the server relays one decoded frame per request at `/api/cameras/frames/traffic-scotland/<sid>.jpg`: sids limited to the last index, 45-second cache of at most 512 frames, two concurrent upstream requests, a 2 MiB frame bound, JPEG magic checked, session revalidated, `private, max-age=30`. A live frame of 7,954 bytes decoded. The site's own map key (Google Maps) was not copied. |
| Durham County Council (`durham`) | Council traffic cameras: positions from the council's Open Government Licence dataset on Data Mill North, images embedded by the council pages from its contractor host `dcc.ussgroup.co.uk` without a key | 30 live sites with an image mapping (one listed site had none). A sample JPEG returned 42,725 bytes without a referrer. Positions are exact; each entry links its council page. |
| UK public streams (`uk-live`) | Curated YouTube embeds owned by councils, harbours, railway trusts, seabird centres, weather sites, hotels and cafes across Scotland, England, Wales and Northern Ireland | 47 streams, each confirmed embeddable through YouTube oEmbed on 14 September 2026 (title and owner recorded). 15 further candidates refused embedding and were dropped. Positions are the locality, approximate. Scotland: Edinburgh, Fort William (two), Linlithgow, Aberdour, Lochgelly, Loch Ness, Glasgow Airport, Stornoway, Greenock, Bass Rock, Loch Arkaig. Gloucestershire: the Dean Forest Railway at Lydney (two). No public stream of Cheltenham itself was found. |
| Estonia, Tark Tee (`estonia`) | Transpordiamet's public DATEX II `roadCameraLocations` publication: position, Estonian name and the current image link on `tarktee.transpordiamet.ee` | 181 locations. The server frames its JSON variant with two Transfer-Encoding headers, which the pinned client refuses; the adapter asks for XML, which arrives with a plain Content-Length. Image links carry a capture timestamp and are refreshed with the 15-minute catalogue. |
| Tallinn junction cameras (`tallinn`) | The city transport department's public junction snapshot page `ristmikud.tallinn.ee`, images at `/last/camNNN.jpg` | 254 cameras listed, 251 placed. The page carries no coordinates, so each junction name was geocoded once with Nominatim during the build and the position is labelled approximate. A sample JPEG returned 60,892 bytes at 1280 by 720. |
| Baltic public streams (`baltic-live`) | Curated YouTube embeds | 6 streams: Tallinn (two), Kuressaare, the RMK Elistvere animal park, Streets in Riga, Riga Zoo. No official Latvian camera index was found: the national access point map publishes no camera layer and the road administration's site has no camera pages. |
| Russia public streams (`russia-live`) | Curated YouTube embeds, principally the Mobotix Webcams Russia channel in Saint Petersburg and the Omsk multichannel camera | 11 streams. Searches for Moscow, Sochi, Vladivostok, Kazan, Yekaterinburg, Murmansk, Kaliningrad, Novosibirsk, Rostov and Crimea in English and Russian returned no owner-operated live camera. Aggregator re-streams of unclear provenance were excluded. |

Not added and why: TrafficWatchNI (Northern Ireland) hotlink-protects its images and its map
data endpoint refuses requests without the site's own session; Traffic Wales embeds a private
API key on its camera page; National Highways publishes cameras only behind a subscription
key; the Scottish city councils' pages returned 403 or 404.

The registry gained 39 hosts and providers in total across this and the eastern module; the
browser allowlist, adapter host sets and the Caddy CSP `img-src` list carry
`tarktee.transpordiamet.ee`, `ristmikud.tallinn.ee` and `dcc.ussgroup.co.uk`. Relayed
frames are same-origin and need no policy change.

## 14 September 2026: official indexes across Europe

A second search looked for keyless official catalogues whose images load without a referrer,
cookie or token. Eight passed, all fetched live through the camera HTTP client
(`camera_europe_open.py` for JSON indexes, `camera_europe_maps.py` for KML and WFS maps).

| Provider (id) | Catalogue and capability | Observed |
| --- | --- | --- |
| Lithuania (`lithuania`) | eismoinfo.lt camera table; positions are LKS-94 grid metres converted with an inverse transverse Mercator that matches PROJ to under a millimetre | 296 snapshots; reuse permitted with credit |
| Ireland (`ireland`) | TII's CARS camera API, public still views | 247 snapshots; TII data is CC BY 4.0, this API is undocumented |
| Norway (`norway`) | Statens vegvesen road weather and camera API. It answers 400 without an `X-System-ID` header, so the adapter sends the fixed public name `theallseeingeye` through a dedicated identified GET that refuses anything resembling a secret | 842 snapshots, 136 HLS streams on `kamera.vegvesen.no` with open CORS |
| Hungary (`hungary`) | Utinform webcam GeoJSON; the image URL is built from place id and camera number, and only cameras with an image under 15 minutes old are kept, as the operator's site does | 482 snapshots, served as `application/octet-stream` without nosniff, so browsers render them |
| Autostrade per l'Italia (`autostrade`) | Motorway webcam JSON with relative frame paths under fixed prefixes | 986 cameras, 830 stills and 981 short MP4 clips on `video.autostrade.it`; no licence found, treat as operator terms |
| Luxembourg (`luxembourg`) | CITA camera KML (CC0 on data.public.lu); images built from the placemark id | 94 snapshots |
| Madrid (`madrid`) | City of Madrid Informo CCTV KML; the image is read from the escaped description and must be on `informo.madrid.es` | 357 snapshots |
| Lyon (`lyon`) | Metropole de Lyon Criter web cameras over WFS GeoJSON | 15 snapshots |

Examined and left out: Germany's Autobahn API (webcams withdrawn), Hamburg and NRW (no image
catalogue or session-bound), Slovenia (encrypted aggregator, NAP needs credentials), Denmark
(no reachable layer), Flanders (embedding refused), Wallonia (session cookie), Czechia
(unreachable), Poland GDDKiA (bot protection), Croatia (no coordinates), Slovakia and Portugal
(no camera layer), Catalonia (http images with redirects), Euskadi (failing image hosts), Anas,
Trento and South Tyrol (none, http only or third-party licence), Istanbul (503) and the
Bulgarian, Romanian, Georgian, Maltese and Cypriot portals (unreachable or positions only).

## 15 September 2026: more UK councils, islands and crossings

A UK-only search added 430 cameras, each catalogue fetched live and every hand-placed image or
stream URL checked the same day.

| Provider (id) | Source | Observed |
| --- | --- | --- |
| North East Traffic Cameras (`northeast`) | The Tyne and Wear UTMC site: positions from the map page's Leaflet settings, images from its camera list, joined by node (`camera_britain_councils.py`). Durham UTMC entries are skipped because `durham` carries them, and images older than 24 hours are left out | 323 cameras across Newcastle, Gateshead, Sunderland, North and South Tyneside and Northumberland, all updated within six hours |
| North Yorkshire Council (`northyorkshire`) | Road weather camera GeoJSON; cameras reporting an error are skipped | 21 cameras |
| Westmorland and Furness Council (`westmorland`) | The weather camera page's station list, images built from each station id | 33 cameras across Cumbria |
| Derbyshire County Council (`derbyshire`) | Traffic camera GeoJSON, which lists coordinates latitude first | 8 cameras |
| UK council, island and crossing cameras (`uk-local`) | Curated fixed URLs with approximate positions: Isle of Man Government harbour and Mountain Road cameras (10), Argyll and Bute Council road cameras (15, positions geocoded from site names), Comhairle nan Eilean Siar road cameras (12), Tamar Crossings bridge and ferry cameras (4), Mersey Gateway HLS streams (2) and Farnham Town Council South Street HLS streams (2) | 45 entries; the Mersey Gateway and Farnham playlists and segments send open CORS. The Isle of Man firewall rejects non-browser clients, but browsers load its images normally |

Examined and left out: National Highways (images go only to nominated media partners over its
Video Information Highway, Crown copyright), Newcastle Urban Observatory (camera brokers inactive
and no positions), Perth and Kinross (no positions), Carmarthenshire (images frozen for a week),
Southampton ROMANSE and Hertfordshire (hosts do not resolve), Nottingham and Reading (TLS
certificate mismatches), Sheffield, Leicester and Bristol open data (locations without images),
Birmingham, Hull, Cardiff, Devon and Smart Cambridge (no image feed), the Humber Bridge
(discontinued), Forth bridges, CMAL harbours and Cairngorm (Traffic Scotland imagery or embedded
players only), Guernsey (timed out), Jersey's airport loop (one camera cycling ten files) and the
community-run Snow Gate Cameras (not a public body).

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

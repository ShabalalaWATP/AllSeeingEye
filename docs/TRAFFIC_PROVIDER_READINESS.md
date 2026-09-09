# Worldwide traffic collection and provider readiness

Reviewed 8 September 2026. This records collection capability, not verified worldwide reception.

## Delivered collection changes

- Existing ADSB.lol military, special-list and 22 priority-area queries remain enabled.
- `adsb_global` adds 1,738 circles covering the sphere geometrically, including oceans and polar regions. Latitude bands are five degrees wide; longitude spacing contracts towards the poles. Every circle respects the documented 250 nautical mile maximum. A coprime permutation interleaves hemispheres instead of fetching one continent first.
- Each sweep poll attempts at most 24 circles, with one second between requests, a five-second request timeout, a 45-second overall budget and the existing 15,000-event batch cap. Failed queries advance the cursor. Source health reports attempted-cell progress, not successful complete coverage.
- A complete attempt cycle needs at least 73 polls, plus provider delays, failures and scheduler jitter. Aircraft expire after ten minutes. The sweep therefore cannot produce a simultaneous whole-world snapshot, and old positions are not retained or relabelled live to create that impression.
- Optional `AircraftInterestQueue` prioritises map centres: at most 32 centres, rounded to one degree, five-minute expiry, four per poll. Register only after authenticating the map request. The `adsb_viewport` collector polls at the domain minimum of 30 seconds; the container supplies the shared queue and authenticated geographic event queries register interests. The existing known-area collector is preserved.
- Aircraft retain their ICAO-based event identity and reported position timestamp across these queries. All three geographical collectors use ADSB.lol, not independent receiver networks.
- AISStream already subscribes to worldwide bounds. Added `LongRangeAisBroadcastMessage` (AIS message 27); older-position flags are rejected, unavailable speed/course sentinels are respected, and its coarser coordinate resolution is retained. This does not establish satellite reception by this provider.
- Interrupted AISStream windows now retain valid positions already received, with a partial-result warning. Message/vessel limits report sampling warnings. Compression, one socket, 40-second windows, the minimum 30-second poll pause, 50,000-message/20,000-vessel caps and all existing secret/transport protections remain unchanged. Gaps between windows remain.

## Provider readiness

| Provider | Official capability | Current integration decision |
| --- | --- | --- |
| [ADSB.lol public API](https://www.adsb.lol/docs/open-data/api/) and [published routes](https://api.adsb.lol/api/openapi.json) | Public ODbL point queries up to 250nm and specialist lists; no public all-aircraft route. [Rate limits are dynamic](https://github.com/adsblol/api/blob/main/README.md). | Enabled priority regions, specialist lists and bounded global sweep. Feeder-only re-api not used. |
| [OpenSky REST](https://openskynetwork.github.io/opensky-api/rest.html) | Anonymous worldwide states: 400 credits daily, four credits for a global request. | Not enabled: [current terms](https://opensky-network.org/about/terms-of-use) require prior written agreement for operational REST use, including an internal automated application. Anonymous reachability is not permission. |
| [adsb.fi](https://github.com/adsbfi/opendata/blob/main/README.md) | Public v3 regional queries, one request per second. Global snapshot is feeder-only. | Not enabled by default: public terms restrict use to personal, non-commercial purposes. A suitable deployment permission decision is required. |
| [Airplanes.live](https://airplanes.live/api-docs/) | Official API documentation page is present. | Current schema/entitlement could not be verified: direct documentation retrieval returned 403 and the readable page exposed no usable specification. No endpoint or entitlement was invented. |
| [AISStream](https://aisstream.io/documentation) | Global-bounds AIS stream, receiver/activity dependent, no delivery guarantee. Requires a key; compression and continuous consumption recommended. | Existing configured provider, now includes validated message 27 and partial-window recovery. |
| [Fintraffic / Digitraffic](https://www.digitraffic.fi/en/marine-traffic/) | Open regional AIS positions around Finnish waterways. | Existing complementary ship provider. Its coverage is regional, not an independent global AIS network. |
| [BarentsWatch](https://developer.barentswatch.no/docs/AIS/live-ais-api/) | Norwegian terrestrial/satellite AIS subject to published exclusions and API access controls. | Requires registered AIS client and OAuth credentials. Not enabled without those credentials. |
| [AIS-catcher community](https://www.aiscatcher.org/feeders) | Public map; API advertised as coming soon for stations, with per-station key. | Not an available anonymous API. Map requests or human verification are not bypassed. |

No additional licensed provider was silently activated. More concurrent worldwide coverage requires a suitably authorised bulk feed, contributing receiver access, or a provider agreement. The map-interest queue improves useful local coverage without disguising this limitation.

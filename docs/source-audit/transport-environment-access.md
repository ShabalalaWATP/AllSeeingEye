# Transport, space, cameras and environmental source access audit

Reviewed **10 September 2026** against the repository at the start of this audit
and the official pages linked below. This is an access and coverage assessment,
not confirmation that credentials have been created or a provider is delivering
data to this installation. Account linking and runtime health are recorded by the
main audit. No account, subscription or API credential was created by this work.

## Findings that change the acquisition plan

The most useful additions are **BarentsWatch AIS**, **dated Copernicus imagery**,
**OpenAQ measurements**, and **global weather context**. Repairing authorised
Washington and Alberta camera access is more concrete than adding another webcam
directory. OS Maps is an existing integration waiting for an operator key if one
is still absent. More orbital-position services are a lower priority: CelesTrak
already supplies a substantial public catalogue, and overlapping delivery
services do not necessarily represent independent observations.

The source catalogue is a mixture of implemented adapters, earlier research and
future candidates. In particular, the original OpenSky and Airplanes.live rows
in `02_DATA_SOURCES.md` must not be read as proof of current authorised use.
`TRAFFIC_PROVIDER_READINESS.md` contains the later, more restrictive decision.

## Existing capability and remaining work

| Area | What the inspected implementation actually has | Access or utilisation gap |
| --- | --- | --- |
| Aircraft | ADSB.lol specialist lists, 22 priority regions, a bounded 1,738-cell global sweep and requested viewport centres | All are the same receiver network. The sweep takes at least 73 polls while positions expire after ten minutes, so it cannot provide a simultaneous global census. Prioritise a permitted second network or an authorised bulk feed, not a larger browser limit. |
| Ships | AISStream global-bounds subscription and Fintraffic Baltic/Finnish coverage | AISStream has 40-second collection windows and intervening scheduler pauses. A persistent bounded connection would improve use of the existing key. Norway/Arctic coverage is a useful independent addition. Open-ocean completeness remains unavailable. |
| Satellite positions | CelesTrak active, stations, military and Skynet selections, local orbital propagation and bounded element cache | Preserve orbital epoch and predicted-position labelling. Extra constellation groups often duplicate `active`. Space-Track may add catalogue/history capabilities, but does not establish independent confirmation of shared GP inputs. |
| CCTV | 57 provider groups, on-demand catalogues, bounded clustering and explicit media loading | This already covers the source groups in the inspected OSIRIS revision. Washington, Alberta, ASFINAG and some other sources are unavailable or access-restricted. Curated links are not verified live streams. Africa, Latin America and parts of Asia remain sparse. |
| GNSS | ASE-derived ADS-B NACp proxy, one-degree cells and aircraft-cell-hour counts; maritime warning text can also flag GNSS | No extra key is needed for the current proxy. Broader aircraft reception improves sampling, but low accuracy does not identify a jammer, prove spoofing or describe ground-level effects. |
| Hazards | USGS, EMSC, GDACS, NASA EONET, FIRMS, NWS and other existing regional/basin bulletins | Broad event coverage is already present. Better area/time querying and provenance are more useful than counting overlapping aggregators as extra confirmation. Global weather and measured air quality are distinct missing context. |
| Basemaps and RF terrain | Existing basemap choices, keyed OS Maps adapter, Terrarium DEM tiles, FOSSGIS Valhalla routes and Photon address search | These are map services, not automatically evidence sources. OS Maps needs its own key; routes and terrain do not. RF limitations require better terrain/clutter inputs and validation, not more basemap keys. |
| Infrastructure | Packaged OSM cable snapshot, 25 approximate public ground-station sites and nuclear inventory | Cable snapshot is the first 2,000 returned OSM ways, yielding 1,999 segments, not a complete global cable database. Improve geographic selection and site provenance before presenting worldwide completeness. |

Repository evidence: [worldwide coverage](../WORLDWIDE_COVERAGE.md),
[aviation](../AVIATION_COVERAGE.md), [maritime](../MARITIME_COVERAGE.md),
[satellites](../SATELLITE_COVERAGE.md), [camera groups](../CAMERA_FEEDS.md),
[GNSS method](../GNSS_AND_MAP_CONTROLS.md), [hazard filters](../HAZARD_FILTERS.md)
and [infrastructure limits](../MAP_INFRASTRUCTURE.md). Counts describe the documented
implementation, not a new live count taken during this sub-audit.

## Account and key acquisition queue

| Priority | Provider | Registration/access decision | Integration decision |
| --- | --- | --- | --- |
| 1 | **OS Data Hub, OpenData plan** | Self-service account for an individual or business; create a dedicated API project and OS Maps API key. Use the OpenData plan, avoiding Premium purchases or assumptions about premium zoom levels. | Existing `ASE_OS_MAPS_KEY` server-side setting. Test one supported GB tile, attribution and unavailable behaviour before activation. [Plans](https://osdatahub.os.uk/plans), [API access](https://docs.os.uk/os-apis/accessing-os-apis/os-maps-api). |
| 1 | **BarentsWatch** | Free user registration, then an **AIS-client** under MyPage. Obtain OAuth `client_id` and `client_secret`, token scope `ais`. Public documentation describes self-registration, not organisation approval for the ordinary open feed. | New backend adapter required. Best immediate maritime addition, especially northern waters. [Client registration](https://developer.barentswatch.no/docs/appreg/). |
| 1 | **WSDOT Traveler Information** | The official API page accepts an email address to deliver an Access Code; no price or organisation-domain gate is stated there. Final service terms still need checking in the actual sign-up flow. | Repair unavailable Washington cameras with the documented `GetCamerasAsJson` operation. Keep the code in server-side secret URL handling. [Registration](https://www.wsdot.wa.gov/traffic/api/), [REST contract](https://wsdot.wa.gov/traffic/api/HighwayCameras/HighwayCamerasREST.svc/Help). |
| 1 | **511 Alberta** | Registered account, then request a developer key from its developer page. It publishes ten calls per 60 seconds. The public page does not claim instant approval or describe a fee. | Repair unavailable Alberta source through `/api/v2/get/cameras`; this explicitly requires the `key` parameter. Preserve image ownership and provider timestamps. [Developer access](https://511.alberta.ca/developers/doc), [camera contract](https://511.alberta.ca/help/endpoint/cameras). |
| 1 | **OpenAQ** | Free individual account/key with a real name and non-disposable email; one key per individual. No organisation-domain requirement is stated. Standard limits are 60/minute and 2,000/hour. | New bounded area measurement provider, not a worldwide polling firehose. Retain original station/provider, pollutant, units, observation period and licence. [Access terms](https://docs.openaq.org/about/terms), [limits](https://docs.openaq.org/using-the-api/rate-limits). |
| 2 | **Copernicus Data Space Ecosystem** | General-user registration and email verification. Optional consents are optional. Paid quota expansions and commercial cloud credits are outside this acquisition run. | New area/date imagery discovery and selected-preview capability. Account enables authenticated downloads/processing; it does not improve orbital marker counts. [Registration](https://documentation.dataspace.copernicus.eu/Registration.html), [free service scope](https://documentation.dataspace.copernicus.eu/Ecosystem.html). |
| Retain | **AISStream** | Existing development key was previously configured. Verify that account/key first; no duplicate sign-up is useful. | Improve continuity and useful metadata retention under existing memory limits. [Official documentation](https://aisstream.io/documentation). |
| Retain | **NASA FIRMS** | Existing development MAP_KEY was previously configured. Keys are emailed free; do not request duplicates merely to obtain more quota. | Verify existing key and each sensor. Current provider limit is 5,000 transactions per ten minutes; larger requests can count more than once. [MAP_KEY service](https://firms.modaps.eosdis.nasa.gov/api/map_key/). |
| Defer | **Global Fishing Watch** | Current API terms require an authorised applicant on behalf of an organisation/entity supporting sustainable ocean use, using a valid organisation email. The supplied personal Gmail address does not establish those conditions. | Valuable historical/derived maritime evidence, but resolve genuine eligibility and non-commercial use first. No invented affiliation. [Current terms, section 2B](https://globalfishingwatch.org/our-apis/documentation/docs/license-rate-limits). |
| Defer | **OpenSky Network** | A free account alone is insufficient: operational REST use in any live/automated application, even an internal non-profit one, needs a previous written agreement. | Seek an appropriate agreement if simultaneous global states are essential. Do not activate anonymous access as a substitute for permission. [Current terms](https://opensky-network.org/about/terms-of-use). |
| Defer | **ASFINAG** | Official partner terms describe prior contact and provision of webcam integration details. The current content portal has public information, but an ungated self-service webcam credential was not established. | Ask for authorised webcam-partner access. Do not copy Basic credentials embedded in third-party code. [Partner terms](https://www.asfinag.at/media/lsgfvnz1/webcam-informationen-durch-webcampartner.pdf), [content portal](https://contentportal.asfinag.at/about). |
| Optional | **N2YO** | Self-service account then a free API key in the profile. Transaction limits differ by endpoint. | Useful for occasional pass predictions, not bulk replication of the globe. Existing CelesTrak propagation is the first choice for current map positions. [API and account instructions](https://www.n2yo.com/api/). |
| Optional | **Space-Track** | Registered access; full current user-agreement and redistribution conditions were not established from the accessible documentation alone. | No activation until actual account terms fit sharing/report retention. Public GP access does not confer access to unpublished military orbits. [Documentation](https://www.space-track.org/documentation). |

The first group contains realistic account actions. A successful registration must
still be distinguished from **credential configured**, **test passed**,
**collector enabled** and **evidence usable in reports**. No new environment
variable is proposed as though it already exists: BarentsWatch, WSDOT, Alberta,
OpenAQ and Copernicus require implementation work before their keys become useful.

## Provider-specific decisions

### Aircraft: obtain genuinely complementary access

[ADSB.lol](https://www.adsb.lol/docs/open-data/api/) remains a public ODbL source.
Preserve its attribution and derived-database obligations. The current application
already uses several routes from that same network. Counting these routes as
independent providers would overstate source diversity.

[adsb.fi's official contract](https://github.com/adsbfi/opendata) permits public
military/identifier queries and v3 radius queries up to 250 nautical miles, at
one request per second. Its all-aircraft snapshot is feeder-only. Public data is
restricted to personal, non-commercial use. An ordinary account would therefore
not create bulk entitlement for ASE. A receiver contribution or appropriate
commercial agreement is a separate decision.

[Airplanes.live's official documentation page](https://airplanes.live/api-docs/)
was reachable through the research tool but yielded navigation rather than a
usable API specification. This pass has not established its schema, entitlement
or redistribution terms. It remains a promising candidate, not an enabled
second network. OpenSky's operational-use requirement is explicit, so the old
catalogue phrase suggesting ordinary hobby/research access is enough must be
superseded by the licence gate above.

Suggested acceptance metric: for the same bounded AOI and observation interval,
record unique additional ICAO addresses, fresher positions and reception gaps.
Preserve provider provenance on duplicate aircraft. A new endpoint is worthwhile
when it supplies additional usable observations or resilience, not merely a
larger reported API count. Military labels remain transmitted/provider metadata,
not verified mission intent.

### Maritime: improve both observation and context

[BarentsWatch's open AIS feed](https://developer.barentswatch.no/docs/AIS/live-ais-api/)
combines Norwegian terrestrial stations, Svalbard, Equinor offshore stations and
Norwegian satellites. Its geography is restricted to Norwegian economic waters
and the stated Svalbard/Jan Mayen zones. It excludes fishing vessels under 15m,
leisure/sailing craft under 45m and data older than 14 days. It is not a free global
satellite-AIS feed. [API terms](https://www.barentswatch.no/en/articles/api-terms-and-conditions/)
normally apply NLOD, allow commercial reuse with attribution, require visible
credit and ask high-traffic users to contact the operator. Dataset exceptions
still apply. A modest shared backend client is the appropriate design.

Global Fishing Watch offers vessel identity from multiple registries, fishing
activity, encounters and potential AIS-dark behaviour, plus radar-detected vessel
products. These are different evidence products from a current AIS marker and
should carry acquisition/dataset dates. [Official API overview](https://globalfishingwatch.org/our-apis/documentation/).
Its API is non-commercial, with 50,000 daily and 1.5 million monthly requests;
dataset-level restrictions and the organisation eligibility condition remain.
The [authentication guide](https://globalfishingwatch.org/our-apis/documentation/docs/authentication)
says tokens are issued immediately and persist, but that does not override the
eligibility terms. Radar detections or an AIS gap do not themselves establish
identity or wrongdoing.

Within ASE, continuous AISStream consumption is a separate efficiency milestone:
one shared socket, backpressure, bounded latest-per-MMSI state, shutdown and
disable handling, then controlled store publication. This would recover gaps
between the existing sample windows without adding a provider. It must not
increase browser retention or create unbounded position history.
The current [stream contract](https://aisstream.io/documentation) also announces
bandwidth-related message dropping for uncompressed connections from September
2026. Verify negotiated compression from `SubscriptionConfirmation`, not only
the client's requested setting. Backend-only access, three connections per
account/IP and reconnect backoff remain relevant.

### Space: add observation context rather than duplicate predictions

[CelesTrak's GP guidance](https://celestrak.org/NORAD/documentation/gp-data-formats.php)
explicitly requires reuse of cached files, no more than one download per update
for enforced groups such as Active/Starlink, and appropriate handling of 403 and
other failures. CSV/JSON support expanded catalogue IDs. Starlink is already a
subset of Active. CelesTrak describes Space-Track as the origin of its ordinary
GP data, so another delivery path for the same elements is not independent
corroboration. Cache and failure resilience remain higher value than adding all
group downloads.

Space-Track documents GP retrieval no more than hourly, under 30 requests/minute
and 300/hour overall, and explicitly recommends combined queries over one query
per object. Some publicly named objects have absent or delayed elements for
national-security or sensor reasons. The account cannot be assumed to fill those
gaps. N2YO provides generated future positions and visual/radio passes, with
1,000/hour TLE and position calls and 100/hour pass/above calls. For bounded
on-demand pass lookup this is reasonable; for every satellite every minute it
adds requests with little new observational evidence.

[SatNOGS Network](https://network.satnogs.org/about/) is a more distinct future
addition: public community ground-station observations and reception context,
with CC BY-SA data. Its [Network API documentation](https://docs.satnogs.org/_/downloads/satnogs-network/en/latest/pdf/)
states open API access. Treat its ground stations as a separate community network,
not a replacement for the curated major government/commercial facilities. No
observation scheduling or remote station operation is needed for a read-only
source. Verify the actual station schema and licence version before importing.

### Cameras: repair known failures and communicate what is playable

Washington and Alberta have concrete official keyed contracts, making them
actionable repair candidates. ASFINAG offers authorised public webcam partner
integration, while its [tunnel video is not public](https://help.asfinag.at/bau-betrieb-und-verkehr/verkehr/verkehrsinfodienste/).
The older partner terms say
linking is generally free but require prior contact; current approval and media
rules still need confirmation. Do not interpret a free partner programme as an
unrestricted recording licence.

Keep per-provider catalogue age, camera capture time, playback method and failure
reason visible. A snapshot, a short MP4 clip, an HLS stream and a provider page
must remain distinct. Catalogue group parity with OSIRIS is not record parity,
continuous video availability or worldwide street coverage. Further expansion
should favour official local transport/environmental catalogues in underserved
regions, after contract and sample verification, rather than wholesale arbitrary
camera-host discovery.

### GNSS: observation quality and official context

[GPSJam's current FAQ](https://gpsjam.org/faq) identifies Airplanes.live and
ADS-B Exchange as inputs, deduplicated per aircraft, and a daily aggregation.
It explicitly says low accuracy is not proof of jamming and blank areas can
mean missing aircraft or receivers. ASE's one-degree, aircraft-cell-hour proxy
is methodologically different, so it must retain its own label and denominator.
No public automated data-redistribution permission for importing GPSJam's derived
dataset was established in this pass.

Prioritise sampling coverage, known-good denominators and original observation
time, plus official navigation warnings already available through relevant
maritime sources. Show space-weather context separately. Do not infer an RF
transmitter location, affected constellation or ground-level impact from the
aviation proxy. A key for another aircraft API improves this only if its terms
permit use and its receiver coverage adds data.

### Environment: build area analysis from measurements and dated imagery

**MET Norway** is a strong first global forecast provider without account setup.
Its default data policy is NLOD/CC BY 4.0 with attribution. Requests require an
identifying contact, sensible shared caching, adherence to `Expires` and
`If-Modified-Since`, and coordinates truncated to at most four decimals.
More than 20 requests/second per application needs agreement; ASE should stay
well below that. [Terms](https://docs.api.met.no/doc/TermsOfService.html),
[licensing](https://docs.api.met.no/doc/License.html).
Use a few representative AOI points, distinguish forecast from measurement,
and retain issue/valid times. Weather at an AOI centroid is not necessarily
representative of a large or mountainous polygon.

**Open-Meteo** is a useful alternative for multiple forecast, historical, marine
and air-quality models, but its free hosted service is non-commercial only,
below 10,000/day, 5,000/hour and 600/minute. CC BY data licensing does not remove
that service restriction. A commercial deployment would need an appropriate
plan or a different authorised delivery route. [Current terms](https://open-meteo.com/en/terms).

**OpenAQ** fills a measurement gap. It is not uniformly CC BY: its licence
resource exposes attribution, redistribution, modification and commercial-use
permissions per licence. Filter/admit datasets using those actual terms and
preserve original provider credit. Coverage gaps, irregular reporting and unit
differences should be explicit; measurements must not become a medical diagnosis
or a fabricated continuous pollution surface. [Licence metadata](https://docs.openaq.org/resources/licenses).

**Copernicus Data Space** provides dated Sentinel optical/radar products suitable
for area/time discovery, clouds and acquisition-quality filtering, and selected
before/after comparisons. Its [STAC catalogue](https://documentation.dataspace.copernicus.eu/APIs/STAC.html)
is an appropriate discovery contract. General-user Sentinel Hub limits currently
list 10,000 requests and 10,000 processing units/month, with 300/minute limits;
these are shared resources, not permission to launch unlimited area analyses.
General free accounts do not include every batch API. [Quotas](https://documentation.dataspace.copernicus.eu/Quotas.html).
Start with metadata, source links and tightly bounded previews. Full-resolution
raster processing needs a separate bounded worker and storage decision.

**NASA GIBS** offers pre-rendered, date-aware visualisations through standard map
services, with acknowledgement requested. It is suitable for contextual imagery,
smoke/cloud observations and night-light browsing. It is not a quantitative pixel
analysis API or a current high-resolution CCTV substitute.
[Official GIBS documentation](https://nasa-gibs.github.io/gibs-api-docs/).

Existing **FIRMS** and **EONET** should cooperate: thermal detections represent
sensor observations, while EONET supplies curated event context and original
source links. EONET v3 supports category, date, status and bounding-box queries;
its bounding-box parameter order is unusual and must be implemented from its
contract. Dataset/source lineage must prevent an EONET event citing a source
already collected directly from being counted as independent confirmation.
[EONET v3 contract](https://eonet.gsfc.nasa.gov/docs/v3).

## Map service and infrastructure decisions

- **Valhalla routing:** the current fixed FOSSGIS origin is covered by its public
  terms, including a maximum one request/second and no availability guarantee.
  There is no missing API key. Retain genuine operator identification and shared
  pacing. [FOSSGIS service terms](https://fossgis.de/arbeitsgruppen/osm-server/nutzungsbedingungen/).
- **Photon:** the public demo allows reasonable project use, with throttling and
  no guarantee. No account is needed for the current address search. Large-scale
  enrichment requires a self-hosted or authorised service; do not use this small
  search endpoint to geocode every incoming headline.
  [Official project policy](https://github.com/komoot/photon).
- **Terrarium terrain:** the existing AWS-hosted dataset is global bare-earth
  terrain, with source-specific attribution linked by the registry. No AWS key
  is needed for the public tiles. Additional zoom does not automatically add
  newer or higher-quality elevation. Buildings, vegetation and local clutter
  remain separate accuracy gaps. [Dataset registry](https://registry.opendata.aws/terrain-tiles/).
- **Cables:** improve geographically balanced OSM extraction and explicit data
  dates rather than lifting TeleGeography's database from a public visualisation.
  The current source and its ODbL provenance are documented in ASE; an additional
  licensed cable database is a separate acquisition, not free map-image reuse.
- **Ground stations:** improve the 25 existing public-site records by operator
  source, function and coordinate quality. SatNOGS can add a distinctly labelled
  reception network, but would not make the major-facility inventory complete.

## Delivery order and success criteria

1. **Connection audit first:** verify existing AISStream, FIRMS and OS keys without
   echoing secrets. Retain a dated result showing access denied, unconfigured,
   transient failure or successful bounded delivery. A key's presence is not a
   successful connection.
2. **Restore known sources:** WSDOT and Alberta authorised camera access, then
   BarentsWatch. For each, test an actual bounded result, timezone, geometry,
   attribution and source disable path before claiming it is linked.
3. **Make area reports richer:** MET Norway weather context, OpenAQ stations and
   Copernicus acquisition metadata/previews. Reuse the existing area-research
   disclosure, budgets, immutable boundaries, receipts and citation validation.
4. **Improve current feed utilisation:** persistent bounded AISStream intake,
   measured aircraft provider comparisons, geographic cable sampling and camera
   health/coverage. Preserve the frontend marker and cache limits that protect
   responsiveness.
5. **Permission-dependent work:** OpenSky written operational access, genuine
   Global Fishing Watch eligibility and ASFINAG partner approval. A request sent
   or account created is not approval and must remain visibly pending.

Every new research receipt should separate **discovery**, **usable evidence** and
**no coverage**. Preserve physical sensor, originating publisher or registry,
observation date, collector and transformation lineage. Multiple providers may
repeat the same satellite element, AIS broadcast, warning or camera feed.
Report confidence must not rise merely because that repeated record passed
through several services.

## Verification limits

This sub-audit used repository/document inspection and official web documentation.
It did not authenticate to private provider accounts, fetch third-party camera
streams, create users, send email, purchase plans, run tests or modify application
code. The NOAA current Kp JSON endpoint was read and uses the numeric-object
format already handled by the inspected `KpConnector`; no schema repair was
needed for the March 2026 format change.

Access facts are dated to this review. Browser-only terms, final registration
eligibility, credential entitlement, dataset-specific reuse and runtime delivery
remain explicit checks at connection time. The main audit owns actual setup
results and must not present this recommendation document as completed linking.

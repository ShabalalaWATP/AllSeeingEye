# Sources and evidence

The All Seeing Eye combines public feeds, question-specific research and reference
layers. These have different jobs: a feed supplies recent observations, a research
provider answers a bounded query, and a reference layer supplies context. A catalogue
entry does not mean that the source is live or that its claims have been verified.

Open **Settings > Sources and connections** to see the installation's current
catalogue, requirements and connection states. Administrators can inspect collection
health and enable or disable sources under **Administration > Sources**. Use these
screens for current availability rather than a fixed source count in this document.

## What is collected

### Scheduled feeds

These connectors populate the shared live event store and the map or specialist
trackers. Some need an operator account or key.

| Family | Providers and material | Main limitation |
| --- | --- | --- |
| Aviation | adsb.lol aircraft positions, military and privacy-list views, squawk and area queries | Receiver coverage is uneven. Missing aircraft are not evidence of an empty sky; a list flag does not prove a mission. |
| Maritime | AISStream, BarentsWatch AIS and Digitraffic vessel positions; NGA maritime warnings | Coverage depends on receivers and provider scope. AIS identity and position are reported data, not authenticated intent. |
| Hazards and weather | USGS and EMSC earthquakes, GDACS, NASA EONET and FIRMS, NHC and JTWC cyclones, NOAA tsunami and NWS alerts, Smithsonian volcano reports and regional warning feeds | Update times and spatial precision differ. Thermal detections are not a diagnosis of what caused a fire. |
| Space | CelesTrak orbital elements, Launch Library 2 and NOAA SWPC alerts, scales and geomagnetic indices | Satellite positions are calculated from orbital inputs, not live visual observations. Launch schedules can change. |
| Conflict and humanitarian reporting | UCDP, optional ACLED and ReliefWeb APIs, ISW assessments, Ukraine General Staff reports, WHO outbreaks and IFRC GO | Event datasets, assessments and participant claims have different methods and delays. A belligerent's loss claim remains attributed to that belligerent. |
| News | Publisher RSS/Atom feeds, regional and language feeds, GDELT and Google News watchlists | Headlines and excerpts are incomplete accounts. Aggregators and repeated headlines do not establish independent corroboration. |
| Social and video | Curated Bluesky author feeds, Mastodon hashtag feeds, public Telegram channel previews and keyed YouTube Data API channel metadata | This is selected public coverage, not a platform-wide archive. No private messages or accounts are collected. YouTube collection does not download videos or transcripts. |
| Cyber and connectivity | CISA Known Exploited Vulnerabilities, ransomware.live, IODA and optional Cloudflare Radar data, plus advisory feeds | Outage signals and aggregated attack distributions do not establish cause, precise targets or attribution. Ransomware claims need verification. |

Publisher feeds include international and regional outlets such as CBC, NPR, PBS,
RFI and The New York Times alongside government, humanitarian and specialist sources.
The catalogue exposes each registered feed's language, source character, attribution
and grading basis. Linked articles can still be paywalled or unavailable.

Feed workers use bounded polling, caching, rate limits and failure backoff. Raw public
events are kept in a bounded in-memory store rather than a permanent event archive.
Reports preserve selected evidence separately. Satellite orbital inputs have a bounded
disk cache; the app does not retain a history of generated satellite positions.

### Research providers

Research collection is scoped to a question, time window and selected sources. It
can also use countries, an area drawn on the map, languages or exact subject
identifiers. Providers run only when selected and admitted within the run's budget.

| Research task | Implemented sources | What the result represents |
| --- | --- | --- |
| News and public discussion | Google News editions, configured publisher feeds, curated Telegram and Bluesky routes, Mastodon feeds and YouTube search | Bounded matching titles, excerpts, dates and links. Curated-account coverage is not general social search. |
| Company and entity research | SEC EDGAR company/submission metadata, selected filing retrieval, Companies House profiles/officers/persons with significant control, GLEIF profiles and accounting parents | Registry assertions and identity candidates. Names and accounting relationships are not proof of beneficial ownership. |
| Domains | Google Public DNS, Verisign RDAP for .com/.net and SSLMate certificate transparency | Current resolver, registry and certificate records. No target-host scan, historical ownership conclusion or complete subdomain search. |
| Scholarship and public policy | OpenAlex, Crossref and UK Parliament written questions | Publication or official-record metadata. Indexing and official publication do not validate the underlying claims. |
| Economics | World Bank annual indicators, ONS UK CPIH and ECB reference rates | Explicit bounded series with recorded units, dates and missing values. These are not a general market-data terminal. |
| Procurement, aid and designations | UK Contracts Finder, an imported AidData catalogue, imported UK Sanctions List and OFAC SDN snapshots | Notices and recorded assertions. A name match is a lead; absence from a bounded search is not clearance. |
| Area and environmental research | Retained geolocated feeds, USGS, EONET, OpenAQ, OpenStreetMap features and packaged asset registers | Records intersecting the supported area/time selection. Coverage can be uneven and some records describe a snapshot rather than a current condition. |
| Satellite acquisition context | Copernicus Sentinel-2 catalogue footprints | Acquisition metadata and footprints, not downloaded or interpreted imagery. |
| Connectivity | IODA outage events, OONI country aggregates and Cloudflare Radar distributions | Bounded observations or aggregate shares, subject to provider-specific permissions. |
| Supplied documents and media | Private TXT, CSV, JSON, PDF and DOCX inputs; supported images and videos | Extracted passages, metadata, OCR and sampled frames. Extraction does not authenticate authorship, capture date or location. |

Selected original-document acquisition has its own source permissions, size and time
limits. Do not assume that every linked page or a complete document was read. Inspect
the saved passages and locators in the evidence view.

Each run records collection receipts: which providers were attempted, what came back,
and whether work was empty, unavailable, unsupported, timed out or limited by budget.
An empty response means that this request found nothing within its limits. It does not
prove that no relevant information exists.

Optional [fresh web research](FRESH_WEB_RESEARCH.md) adds AI-generated discovery
context with provider citation annotations. It remains separate from the graded
evidence base. See [AI in the app](AI.md) for how that distinction is enforced.

### Maps, cameras and reference material

The source catalogue also lists data used outside the feed scheduler:

- Base maps and request-time services, including OpenFreeMap, terrain, place search,
  routing and optional Ordnance Survey mapping.
- Public camera indexes and curated camera catalogues. Listing a camera does not
  guarantee that its current stream is accessible.
- Packaged infrastructure registers for energy, data centres, semiconductors, cables,
  nuclear facilities and satellite ground stations.
- Country outlines, reference entities and aircraft types, plus curated Ukraine
  tracker material and source-linked reference records.

Snapshots carry their own attribution and dates. A mapped site is not confirmation
of its present operation or ownership. Browser-loaded maps and camera services can
receive the browser's network address and requested view.

## Understanding availability

| State | Meaning and next step |
| --- | --- |
| Live / connected | The scheduled source has collected successfully. Check the last update and item dates before treating it as current. |
| Live with warning | Collection succeeded with a stated coverage limit, such as a sampled worldwide sweep. It counts as live; read the warning before interpreting gaps. |
| Waiting / idle | No collection has completed yet. A configured key can still be unverified. Allow for the source's polling interval and inspect its details. |
| On demand | The capability runs when research or a map interaction needs it. It is not a failed scheduled feed. |
| Available | A packaged snapshot or catalogue is present. This says nothing about current upstream availability. |
| Needs key or setup | A required credential, local dataset, runtime or acknowledgement is absent. The detail names the requirement. |
| Retrying / degraded | Collection or an upstream refresh encountered a problem. Retained data may still be available. Failed requests use backoff. |
| Failing | The administration overview groups degraded and paused collectors here. Inspect the cause; a source paused after repeated failures needs an administrator's review before reset. |
| Blocked upstream | The provider has refused this client, registration or account tier. Repeated resets do not resolve access restrictions. |
| Switched off | An administrator or the installation's configuration disabled it. |

Research health cannot be established without a query. Camera status can reflect a
cached refresh. A key being present is a configuration fact, not a successful test.
For the full state definitions, see [Sources and connections](SOURCES_AND_CONNECTIONS.md).

## Optional accounts and data

Public feeds work without configuring every integration. Enable only the sources
needed for your use and review their reuse terms.

| Capability | Configuration requirement |
| --- | --- |
| AISStream and BarentsWatch | Provider API key or client credentials |
| NASA FIRMS area API | MAP_KEY, entered in its administrator connection or the documented environment setting; public FIRMS collection is also supported |
| ACLED and ReliefWeb APIs | An eligible ACLED account/token or an approved ReliefWeb application name |
| YouTube | YouTube Data API key; there is no unauthenticated channel-feed fallback |
| Companies House, SSLMate and OpenAQ | Separate provider keys |
| UCDP and OpenAlex | Optional authenticated routes; the app also implements public access |
| Cloudflare Radar research | Token and explicit suitable-use acknowledgement |
| OONI and IODA research | Explicit acknowledgement of the relevant data-use terms |
| AidData and sanctions research | Validated local catalogue or snapshot import |
| OCR and video extraction | Local extraction tools supported by the installation |

The exact setting names are in [`.env.example`](../.env.example). Keys belong in the
server's configuration or the relevant administrator form, never in source files,
research questions or screenshots. A source being publicly accessible does not grant
unlimited redistribution rights; keep its attribution and reuse conditions.

## Evidence grades and provenance

The app separates **source reliability (A-F)** from **item credibility (1-6)**.
F and 6 mean that reliability or credibility cannot be judged, not that an item is
false. Research sources without an assessed basis remain explicitly unassessed.
Configured feed grades include their recorded basis and limitations.

Automatic topic matching can identify related reports, but cannot prove independent
agreement. The same claim repeated through several aggregators is not several
independent sources. Publisher, account and organisation metadata can be incomplete
or declarative rather than verified.

Reports freeze selected evidence, grades, provenance and relevant dates so a later
catalogue change does not silently rewrite an earlier assessment. Links, locators and
hashes help trace material; they do not authenticate the original or preserve an
entire website. Publication, collection and claimed event dates remain separate.

Read [reporting and assessment](03_DOCTRINE_AND_REPORTING.md) for grading and
confidence rules, [source provenance](SOURCE_PROVENANCE_OPERATIONS.md) for date and
language handling, and [source catalogue browsing](SOURCE_CATALOGUE_BROWSING.md) for
finding a suitable provider.

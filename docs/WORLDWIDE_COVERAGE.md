# Worldwide map coverage

Updated 9 September 2026. Geographic reach is different from complete or continuous
observation. Empty areas can indicate missing reception, expired positions, disabled
sources or a bounded sample; they do not prove absence of activity.

| Layer | Worldwide capability | Important limits |
| --- | --- | --- |
| Aircraft | ADSB.lol specialist lists, 22 priority areas, a 1,738-cell whole-Earth sweep and collection around requested map centres | One receiver network; at most 24 sweep queries per two-minute poll plus execution/jitter. At least 73 polls per cycle. Ten-minute freshness means this is not simultaneous worldwide visibility. Receiver gaps and non-broadcasting aircraft remain absent. |
| Ships | AISStream worldwide subscription plus regional Fintraffic data; long-range AIS message 27 added | Reception/transmissions determine coverage. Forty-second collection windows with a minimum thirty-second pause remain. Long-range message format does not establish satellite AIS reception. Interrupted windows preserve valid positions. |
| Satellites | Existing global CelesTrak active catalogue and stations, public military and Skynet selections | Public orbital predictions, not live observations. Original element age and download limits remain. Undisclosed orbits cannot be invented. Map requests now sample geographically and fetch relevant retained positions on zoom. |
| FIRMS | NOAA-20 and NOAA-21 global VIIRS observations from NASA, using the existing key or approved public files | Cloud, overpass and measurement limits apply. Validate up to 150k rows/16MiB per sensor, retain a geographic sample of at most 10,000 per sensor across keyed/public delivery. Counts are observations, not confirmed fires or attacks. |
| Earthquakes/disasters | Existing global USGS, EMSC, GDACS and EONET sources, supplemented by basin/regional alerts | Reporting thresholds, update delays and national coverage differ. NWS remains a US source. |
| Conflict/news | Existing worldwide GDELT and UCDP coverage, plus configured regional/news sources and optional approved APIs | Publication bias, historical monthly datasets and source access limits remain visible. Reports are not all independently confirmed conflict incidents. |
| CCTV | Existing 57-provider regional catalogue, progressively loaded and geographically clustered | Operators enable regions in the CCTV panel. Public provider availability and sampling differ; no camera network covers every country or street. |
| Cables/ground stations | Existing public global infrastructure catalogues and curated known facilities | Published inventory and approximate locations, not live operational status or a complete military infrastructure register. |

## What changed

The map previously selected the newest records before its response limit. A dense
local feed could therefore hide other regions even when their data was retained.
`GET /api/events?sampling=geographic` now rotates geographic cells, then categories
within cells, before applying the response limit and offset. Default newest-first
queries are unchanged. Existing source/country/time/military filters run first.
Unlocated reports are not assigned invented coordinates.

The browser remains bounded to 5,000 records. Initial and supplementary snapshots
are geographically balanced. After an 800ms camera-settle delay, zoomed views load
one current bounding-box snapshot; zooming out restores global sampling. All
supplements share this scope and old in-flight requests are cancelled. Incoming
positions outside the current scope cannot crowd it out. Military and specific
satellite priorities remain. Low-zoom aircraft/ship icons also use geographic
selection; no GPU marker limit was increased.

Authenticated geographic map queries can request an aircraft centre. A shared
queue holds at most 32 rounded centres for five minutes, four collected per poll.
Admission is limited to 60 hints per minute per user; excess hints do not prevent
reading cached data. The collection source respects ordinary source controls.
Full-world queries use the sweep instead. This is a radius-based collection hint,
not a promise to collect every aircraft within a large viewport immediately.

FIRMS validation and display retention are separate. A retained NOAA-21 file held
111,691 observations, estimated at 642.9MiB if retained as events, exceeding the
entire default 512 MiB store. Selection now preserves occupied 5-degree cells plus
newest observations while bounding intermediate objects. Cumulative limits combine
public/keyed delivery by physical sensor, cap both sensors at 20,000 events, and run
before global memory eviction. Background parsing is serialised and cancellation
cannot launch overlapping abandoned workers. Sampling totals/method and negative
reported power quality flags remain explicit in observation metadata. Keyed
requests cover the current and previous UTC calendar dates, avoiding an empty
new-day window immediately after midnight; this is not a rolling 24-hour promise.
A measured successful request took 61.74 seconds. The two keyed sensors now have
a 120-second default collection deadline, while other feeds retain 60 seconds.
Explicit caller deadlines remain authoritative.

The first 20,000-per-sensor trial still crowded news and conflict records out of
the shared cache during live collection. The final 10,000-per-sensor limit retained
all 561 occupied geographic cells in the saved NOAA-21 sample, estimated at
70.6 MiB per sensor (141.2 MiB combined), while leaving room for other categories.

## Provider access

See [traffic provider readiness](TRAFFIC_PROVIDER_READINESS.md) for verified APIs,
terms and access gates. No licensed, feeder-only or unverified endpoint was enabled
as an anonymous workaround. No purchase or new provider account was made.

[Space-Track GP data](https://www.space-track.org/documentation) is a possible
registered-account orbital catalogue alternative. [N2YO](https://www.n2yo.com/api/)
is keyed and better suited to individual satellite lookups. Neither is enabled
without the necessary credentials. Overlapping orbit providers may redistribute
the same underlying evidence rather than independently corroborating it.

## Validation

- 1,293 frontend tests passed: 95.35% statements, 90.31% branches, 93.74% functions,
  96.72% lines. Full lint, TypeScript and production build passed.
- 215 combined backend regression tests passed, followed by 15 checks for review
  fixes to full-world interests and FIRMS parent-source admission.
- Focused new backend modules reached 95.36% branch-aware coverage across 52 tests.
  Traffic diagnostics subsequently passed 23 tests at 96.30% scoped branch-aware
  coverage. The final FIRMS retention changes passed 77 relevant tests. Thresholds
  remain 90%. The UTC-midnight fix passed 47 focused tests, and final catalogue,
  retention and traffic checks passed 35 tests. The source-specific deadline
  change passed 28 scheduler and deadline tests.
- Backend Ruff, formatting, mypy across 712 modules and both architecture contracts passed.
- Scoped review checked bounded requests/retention, provider URL restrictions,
  credential isolation, source disable controls and cancellation. No arbitrary
  upstream URL, new secret storage or database migration was introduced.
- Interactive local/GPU verification remains unavailable under the existing
  browser policy block; unit/integration checks do not establish a visual soak test.


## Local activation check

After the local API restart, authenticated requests confirmed `adsb_global`,
`adsb_viewport` and `firms_viirs_noaa21` were registered. The first retained counts
were 16,651 space events, 7,985 maritime events and 40,963 disaster events. Geographic
samples of 2,000 space, maritime and disaster records each included northern,
southern, eastern and western hemisphere positions. These are changing startup
samples, not guarantees or a census. An authenticated Chile bounding-box request
was accepted to exercise viewport aircraft collection; initially no aircraft were
retained in that box. No test manufactured records for the running server.


Final activation after the UTC-midnight and deadline fixes retained NOAA-20 and
NOAA-21 successfully: 55,270 and 55,917 validated observations respectively, each
sampled to 10,000 records. The same snapshot retained 11,782 maritime, 16,651 space,
366 aviation, 2,004 conflict and 1,007 news records, plus other categories.
Estimated event-store use was 339.1 MiB of 512 MiB, not a total process-memory
measurement. Maritime, space and disaster samples again included all four
hemispheres. These changing startup counts do not measure complete coverage.
The frontend login endpoint returned HTTP 200. Flight query HTTP failures remain
explicit diagnostics and must not be interpreted as an absence of aircraft.

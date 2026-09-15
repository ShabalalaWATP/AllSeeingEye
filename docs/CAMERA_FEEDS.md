# Public camera feeds

Expanded on 8 September 2026. Open CCTV on the left, enable public cameras,
then switch on a region and search or select a marker. The globe and flat map
share selection and filters. Closing details removes the selection highlight.

## Coverage and playback

The registry then contained 57 source entries (98 providers by 15 September 2026, each listed
on `/sources`) covering every CCTV source group in
OSIRIS revision `fac8d1b1dd3f9aab87bdeccdd04f05c25d5a3bb8` inspected for this work.
This is source-group coverage, not a guarantee that every upstream camera is
available. Providers change their catalogues and access policies. Empty, blocked
and retired sources report their actual status instead of fabricated cameras.

The original TfL, Hong Kong and Fintraffic sources load first. Additional regions
load on demand. The source list shows not loaded, available, stale or unavailable.
Search and pagination expose cameras that overlap on the map.

- [Americas source inventory](CAMERA_AMERICAS.md): 21 providers, including US state
  transport agencies and Canadian provincial and city catalogues.
- [European source inventory](CAMERA_EUROPE.md): 18 providers, including official
  traffic sources and attributed regional webcam directories.
- [Asia and worldwide inventory](CAMERA_WORLD.md): 15 providers, including
  Australia, New Zealand, Singapore, Taiwan, Japan, regional webcams, Skyline
  links and three bounded OpenCCTV regions.
- Original sources: TfL, Hong Kong Transport Department and Fintraffic.

OSIRIS reference: https://github.com/simplifaisoul/osiris/tree/master/src/app/api/cctv
Adapted directory data retains MIT attribution and licence text in the regional
inventories and generated catalogue files.

Play video starts supported HLS, embedded video, MJPEG or MP4 media. MP4 is labelled
as a provider clip. Streams are not presumed live merely because a URL exists.
Provider restrictions, delays and outages still apply. Stop video or closing
camera details releases the player. Provider website links remain available when
embedding is unsupported. Approximate directory coordinates are explicitly labelled.

Load image requests a snapshot and Refresh image requests another. The original
three sources are still-image services. Unknown capture times are not replaced
with metadata retrieval times. Snapshots expire after 15 minutes and loading has
a 20-second deadline. No automatic recording or evidence capture is added.

## Boundaries

The authenticated API revalidates the session after provider work. Catalogues
remain in memory, with at most 5,000 cameras per provider, a 15-minute cache,
one-minute failure retry and 24-hour maximum stale age. Four upstream fetches run
at once. The 45-second fetch deadline starts after the concurrency queue and lock.
The dedicated HTTP client bounds responses to 10 MiB, pins public DNS addresses,
rejects redirects and does not forward application credentials. OpenCCTV metadata
POSTs have a 64 KiB body cap and fixed destinations. No arbitrary proxy is exposed.

Media loads only after an explicit request. Exact HTTPS host allowlists constrain
images, streams and frames. HLS manifests, segments and keys are checked on each
request, omit credentials and reject redirects. TfL S3 images are restricted to
its bucket path; S3 streams are rejected. Embedded providers receive the site
origin as referrer where their player requires it. Caddy CSP mirrors approved
media/frame hosts. Local Vite playback does not verify a deployed Caddy policy.

## Verification

- 152 focused backend camera tests pass. Whole-backend mypy passes across 680 files.
- Actual browser playback of Burgas Smart Burgas HLS reached readyState 4,
  1920 by 1080 video and over 108 seconds of playback.
- Provider probes also returned valid HLS manifests from Caltrans, Nevada,
  Louisiana, Serbia and North Macedonia. This does not establish every stream's
  browser playback. Quebec clips returned 403 and an Indiana stream returned 503.
- ASFINAG requires authorised access. Retired or failed endpoints remain visible
  as unavailable; no embedded credentials or access bypasses were copied.

Existing local alerts still return HTTP 500 because the operator database lacks
`alerts.annotation_monitor_id`. No operator database migration was performed.
Basemap sprite warnings and the existing production bundle warning are separate.

Final integration checks: production build, frontend lint and both TypeScript
configurations pass. Seventeen focused frontend camera tests pass. Dependency
audit reports no known production vulnerabilities. Exact-host parity was checked
between adapter declarations, the browser allowlist (72 media hosts, two frame
hosts) and Caddy. Architecture contracts and source-file length checks pass.
This is scoped security review and regression verification, not a repository-wide
security audit or proof that every provider stream is available.

Final full frontend regression: 1,152 tests across 229 files passed, with 95.26%
statement, 90.07% branch, 93.70% function and 96.62% line coverage. All configured
90% thresholds remain unchanged.


## 15 September: more UK councils, islands and crossings

The North East's Tyne and Wear camera network (323), North Yorkshire (21), Westmorland and
Furness (33) and Derbyshire (8) now load from their councils' public pages, and a curated set of
45 Isle of Man, Argyll and Bute, Western Isles, Tamar Crossings, Mersey Gateway and Farnham
cameras and streams was added. National Highways remains unavailable because its images are
licensed only to nominated media partners. Details are in `docs/CAMERA_EUROPE.md`.

## 14 September: a worldwide official-source sweep

Thirty more official keyless providers joined the registry after live verification: sixteen
US and Canadian 511 systems (twelve on the IBI platform, four through a generic Castle Rock
CARS adapter, with New York and Minnesota HLS streams), eight European national or city
operators (Lithuania, Ireland, Norway with streams, Hungary, Autostrade per l'Italia with MP4
clips, Luxembourg, Madrid, Lyon), Queensland and Puerto Rico. Together they returned about
11,700 cameras on 14 September 2026. Streams are offered only from fixed hosts that answered
with open CORS and unsigned URLs; tokenised Kansas streams and Iowa's port-8888 streams are
not. The per-region tables in `docs/CAMERA_AMERICAS.md`, `docs/CAMERA_EUROPE.md` and
`docs/CAMERA_WORLD.md` list every source and every refusal.

## 14 September: every region on by default

Opening CCTV from the map's camera button now switches public cameras on, and the button stays
lit while they are shown, so the panel switch and the rail button always agree. Every provider
the server lists starts switched on: the first three answers name the rest, which then load
four at a time. A region the user switches off stays off, including after a catalogue refresh.
A live count on 14 September found 67 providers returning about 32,000 cameras in 27 seconds
of server time, well under the 75,000-camera browser cap.

## 14 September: Britain, the Baltic states, Russia and the Middle East

Ten providers joined the registry on request: Traffic Scotland's 415-camera official
index with a same-origin frame relay (the first provider whose images the server
relays, because the operator only serves them inline), Durham County Council's 30
open-data sites, Estonia's 181-location DATEX II publication, Tallinn's 251 junction
snapshots and six curated stream groups (UK 47, Baltic 6, Russia 11, Israel 5, Iraq 3,
China 8), every stream confirmed embeddable through oEmbed that day. Details and the
providers that were examined and refused are in `docs/CAMERA_EUROPE.md` and
`docs/CAMERA_WORLD.md`. The relay is not a proxy: it accepts one provider, sids from
that provider's last index only, bounds each frame to 2 MiB and JPEG, caches for 45
seconds and revalidates the session. Nineteen backend tests across the two new modules,
one feed-client test for the Accept override and twelve frontend camera tests cover the
parsers, the relay, host policy, the frame path rule and the panel groups.

## 8 September: regional discovery and partial catalogues

Compared the 57 ASE providers with OSIRIS commit
[fac8d1b](https://github.com/simplifaisoul/osiris/blob/fac8d1b1dd3f9aab87bdeccdd04f05c25d5a3bb8/src/app/api/cctv/route.ts).
The main provider families are already represented. This does not prove identical
camera records or current playback for every camera. A bounded DriveBC probe
returned 1,062 records which all parsed successfully.

The CCTV panel now groups providers by region with enable/disable controls and
country/provider search. Three initial providers remain the default, loaded independently; operators
can load additional regions from this panel. Completed provider responses appear
progressively, coalesced over 100 milliseconds, instead of waiting for every
slow request. Four concurrent browser requests and the 75,000-record CPU cache
remain bounded. Camera graphics use counted spherical clusters with at most 2,000 representations,
including the selected individual. Offscreen cameras are culled from drawing,
not the searchable catalogue, so zooming into a region can unpack its cameras
without far-away records forcing coarse clusters. Date-line bounds are handled
explicitly. Media is requested only after selection, not for every loaded marker.

OSIRIS's [directory adapter](https://github.com/simplifaisoul/osiris/blob/fac8d1b1dd3f9aab87bdeccdd04f05c25d5a3bb8/src/app/api/cctv/opencctv.ts)
uses the same 1,200/800/600 regional sampling limits as ASE, rather than full
pagination. ASE now shares its bounded marker index across the three directory
regions and retains successful batches when others fail. Index requests have a
12-second deadline; batch work has a 28-second budget and five-second request
limits inside the existing service deadline. Partial results have a visible
warning and become eligible for retry after one minute on a later request.
No unauthorised camera host, embedded provider credential or arbitrary media
proxy was added. Public demo HTML was inspected; interactive demo/local GPU
verification was unavailable because browser policy verification blocked access.

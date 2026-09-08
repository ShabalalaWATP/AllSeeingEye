# Public camera feeds

Expanded on 8 September 2026. Open CCTV on the left, enable public cameras,
then switch on a region and search or select a marker. The globe and flat map
share selection and filters. Closing details removes the selection highlight.

## Coverage and playback

The registry now contains 57 source entries covering every CCTV source group in
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

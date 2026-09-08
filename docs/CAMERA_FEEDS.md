# Public camera feeds

Implemented 8 September 2026. Use the left CCTV button, enable Show public
cameras, then select a marker or search the catalogue. Selecting a list entry
moves the map to the camera. Load image requests one snapshot; Refresh image
requests another. Closing details, switching source filters or disabling cameras
clears the selection highlight. The same controls work on globe and flat map.

## Sources and reference

OSIRIS uses official traffic/weather camera catalogues alongside regional webcam
and broadcaster links. Reference code was inspected, not copied:
https://github.com/simplifaisoul/osiris/tree/master/src/app/api/cctv

| Provider | Official catalogue | Read-only adapter probe |
| --- | --- | --- |
| TfL | https://api.tfl.gov.uk/Place/Type/JamCam | 840 available locations |
| Hong Kong Transport Department | https://static.data.gov.hk/td/traffic-snapshot-images/code/Traffic_Camera_Locations_En.xml | 1,013 locations |
| Fintraffic | https://tie.digitraffic.fi/api/weathercam/v1/stations | 782 collecting stations |

Counts are observations from this run, not guaranteed coverage. TfL unavailable
cameras and Fintraffic stations/presets outside collection are excluded. Fintraffic
uses the first active preset per station. These are still-image feeds, not
continuous video. Capture time is unknown where the catalogue does not supply it;
metadata retrieval time is never presented as image capture time.

Provider guidance:
- TfL: https://tfl.gov.uk/info-for/open-data-users/our-open-data
  Preserve complete images and embedded attribution; hide images after 15 minutes.
- Hong Kong: https://data.gov.hk/en-data/dataset/hk-td-tis_1-traffic-snapshot-images
  Provider service/outage placeholders may be returned as valid images.
- Fintraffic: https://www.digitraffic.fi/en/road-traffic/
  Approximately ten-minute image updates, attributed to Fintraffic under CC BY 4.0.

## Boundaries

GET /api/cameras requires a current active session and revalidates it after
provider work. Camera facilities stay in a separate bounded in-memory catalogue;
no database migration or raw image persistence is introduced. Upstream requests
use fixed URLs and the existing DNS-pinned 5 MiB HTTP client, no redirects and
15-second per-provider deadlines. The cache holds at most 1,500 locations per
provider, refreshes after 15 minutes, retries failures after one minute and drops
stale metadata after 24 hours. Provider failures are reported independently.

Images load directly from exact approved HTTPS hosts after a user request, with
no referrer or ASE token. The server is not an arbitrary image proxy. Canonical
image URLs are validated before a locally generated refresh token is appended.
Image loading times out after 20 seconds; late callbacks cannot restore expired
images. Refresh requests bypass reuse of the prior browser-cache URL. Caddy CSP
permits only the three image providers, restricting the TfL S3 bucket path.

The paginated catalogue exposes overlapping markers through a searchable list.
There is no camera clustering, automatic video playback, recording or evidence
capture in this milestone. Other OSIRIS regions require their own provider
verification and adapters; they are not silently represented as connected.

## Verification

- Eighteen offline backend tests pass, camera-module coverage 98.88%.
- Whole-backend mypy passes across 659 files; Ruff/format and import architecture
  checks pass for the backend change.
- Full frontend regression: 1,145 tests across 227 files pass, 95.27% statements,
  90.08% branches, 93.68% functions and 96.62% lines. Thresholds unchanged.
- Fifteen final focused frontend tests pass after callback/lint cleanup.
- Authenticated browser loaded and decoded actual snapshots from all three
  providers. Physical marker clicks opened camera details on both projections.
  Mobile preview and close controls were inspected at 390 by 600.
- Review identified browser cache reuse and deeply nested provider JSON handling;
  both were repaired with regression tests.

Existing local issues observed separately: alerts return HTTP 500 because the
operator SQLite database lacks alerts.annotation_monitor_id; map basemaps report
missing circle-11/wood-pattern sprites. No operator database was migrated.
The production build retains its existing large-bundle warning. Caddy was not
deployed as part of local Vite verification.

Final presentation verification: eight camera tests and production build pass
after moving metadata below the preview. Thirty combined backend camera and
health/error tests pass. Final lint and both TypeScript configurations pass.
The file-length check passes; GlobePage remains a 353-line composition module
after extracting scene composition and navigation hooks.

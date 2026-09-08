# Map performance repair, 8 September 2026

The earlier instrument-grading repair removed one quadratic allocation, but did
not address large stream frames, repeated browser mirror updates, camera request
bursts or the remaining narrative comparison paths. Functional test success alone
did not establish stability under the expanded feed load.

## Evidence collected

- The existing backend used approximately 1,013 MiB working set and 1,618 MiB
  private memory, with a peak working set of 1,153 MiB. These process figures are
  not the size of the event store alone.
- Forty live health requests before the repair had no failures: median 12.9 ms,
  maximum 251.5 ms. Quiet-period responsiveness did not rule out burst stalls or
  browser memory pressure.
- A synthetic 30,000-record publication produced a 17.3 MB SSE frame and required
  2.15 seconds of synchronous serialisation. The traced benchmark peak was
  92.3 MB. A bounded refresh notification reduced this to a control message of
  tens of bytes; the benchmark peak fell to 30.7 MB. This is a transport benchmark,
  not a browser frame-rate measurement.
- The old store estimate reported 9.3 MB for 28.2 MB of traced retained data. The
  revised estimate reports a conservative 51.3 MB for 30.2 MB retained with the
  added source index. The 512 MiB store budget is not a whole-process memory cap.
- A browser-store benchmark with 5,000 retained records and 2,000 updates across
  200 frames took 834.6 ms before coalescing and 21.7 ms afterwards. Notifications
  fell from 200 to one, with identical retained records. Timing is diagnostic;
  deterministic tests assert the work counts and final data instead.

## Changes and boundaries

The bus limits queued messages and large event batches before per-client
serialisation. Normal bulk updates request a bounded canonical snapshot without
blanking the map. Actual stream gaps and expiry barriers keep their stronger
reconciliation behaviour. Browser resync bursts produce one follow-up request,
instead of repeatedly cancelling useful work. Stream parsing has a fixed one-MiB
frame buffer, handles split UTF-8 and CRLF, and releases readers on exit.

The client combines event updates over 250 ms with a 5,000-ID pending limit.
Health messages do not force an early sort. Hidden tabs disconnect live feeds and
obtain fresh authenticated snapshots on return. The existing source reservations
and 5,000-record map limit remain in place.

Both map canvases cap pixel ratio at 1.5; the map tile cache is limited to 128.
Overlapping-object picking uses at most eight GPU passes. Destroying a map releases
layer and development-console references. These bounds reduce graphics work, but
cannot guarantee a particular GPU or driver will never lose its context.

Camera downloads run at most four at once. Cached region toggles make no request;
adding a region requests that region only, while explicit refresh revisits enabled
regions. The bounded cache is the sole owner of camera records, so evicted regions
cannot survive indefinitely in the rendered catalogue. Partial refresh failures
retain available cached data. Hidden tabs unload requested HLS, embedded video,
MJPEG and MP4 players, resuming the chosen playback when visible again.

Backend processing yields between bounded batches; FIRMS parsing runs outside the
event loop. Source-filtered snapshots inspect the source index instead of scanning
and sorting the entire store. Common headline tokens cannot create a quadratic
pair dictionary: approximate candidates are bounded to 128 per item and frequent
postings are capped. Exact token duplicates retain linear links. The live narrative
context uses the newest 1,000 records in the affected category. Incoming instrument
records are assessed separately in linear time, including those outside that window. Saturated topics
may remain separate; these navigation groups never establish corroboration.

The clocks are six pixels above the bottom safe area. Coordinates sit immediately
above the clock strip, with additional clearance on narrow screens. Removed the
older CSS overrides that forced both controls higher up the map.

## Verification limits

Regression coverage includes burst coalescing, stale snapshot rejection, queue and
frame limits, bounded candidate work, camera concurrency/eviction, cancellation,
hidden-tab cleanup, and preservation of authorisation and source-release guards.
Visual GPU verification remains blocked by administrator browser-control policy.
No operator database migration or production infrastructure change is part of this
repair. The pre-existing local alerts schema mismatch remains separate.


## Post-repair checks

The cooperative normalisation/country pipeline processed 30,000 synthetic records
in 1.477 seconds versus 1.240 seconds synchronously, while reducing the maximum
observed event-loop pause from 1.240 seconds to 0.043 seconds. This trades a little
throughput for responsiveness. Tests assert bounded yields rather than timing.

After the verified local backend restart, 40 further health requests all succeeded:
median 12.9 ms, maximum 107.5 ms. A later authenticated check found 67,718 retained
records with a conservative store estimate of 373.6 MiB; both AISStream and FIRMS
returned populated snapshots. An early post-restart process sample showed 421 MiB
working set and 1,008 MiB private memory. These short observations do not constitute
a long-duration soak test or a claim of a whole-process 512 MiB memory limit.

Backend validation: 158 targeted tests passed, including stream authority,
credential release, store consistency, burst bounds and grading regressions. Ruff,
formatting, mypy across 690 files, and both architecture contracts passed. The new
candidate module measured 98.33% branch-aware coverage. No full-backend coverage
claim is made. Production frontend build and lint passed; its existing bundle-size
warning remains.


Final frontend gate: 1,210 tests passed across 239 files with four workers.
Coverage was 95.36% statements, 90.19% branches, 93.70% functions and 96.71% lines.
The existing map interaction test now waits for the deliberate batch boundary,
including expiry, instead of assuming synchronous delivery. Thresholds were not
lowered. The final build, lint and type checks passed.


## 8 September: rotating globe overlays and graphics failure

The installed deck.gl 9.3 GlobeViewport did not apply bearing or pitch to its
view matrix. MapLibre rotated the basemap while those overlays kept a north-up
projection. This explains the reported separation without assuming that a
north-down map or its geographic labels are themselves corrupted. A numerical
regression checks bearing 180 degrees and pitched projection/unprojection.

The old Mapbox adapter also depended on MapLibre internals removed in version 6.
The app now pins deck.gl core/layers and the dedicated MapLibre adapter to 9.4.0,
using the documented public camera integration. References:
[MapLibre adapter](https://deck.gl/docs/api-reference/maplibre/overview) and
[MapLibre 6 compatibility issue](https://github.com/visgl/deck.gl/issues/10501).

The overlay controller retains the newest layer set, releases failed renderers,
waits for map context restoration, bounds overlay recovery to two attempts and
shows recovery/failure status. Generation guards ignore delayed callbacks from
disposed renderers. An explicit Reload map action recreates the engine while
preserving camera, style, lite mode and data; there is no automatic page reload
loop. Graphics loss invalidates image exports instead of returning a partial
capture. Existing pixel-ratio, tile-cache and event-count limits remain in place.

The original React Bits eye now releases its animation and GPU resources on
initialisation, rendering or context-loss failures. It then retains the existing
original frame capture instead of repeatedly trying to allocate another context.
Shader/noise code was extracted without changing the visual algorithm. Four
lifetime tests cover failed startup, context loss, rendering errors and unmount.

Validation: 1,288 frontend tests across 256 files passed (95.32% statements,
90.31% branches, 93.69% functions, 96.70% lines), including camera clustering,
progressive initial loading and the stale-callback recovery regression. Backend regression checks passed 169 tests covering camera
catalogues, traffic, API bounds, store retention and scheduling. Full backend
Ruff/formatting, mypy (704 modules) and both architecture contracts passed.
Frontend lint, TypeScript and production build passed. No coverage threshold was
lowered. Live traffic samples included 314 provider-labelled military aircraft,
three AIS-labelled military vessels and 291 regional aircraft records after the
bounded collector repair; these are changing samples, not complete inventories.

These are regression and source-level checks, not a live GPU soak test. Browser
policy verification blocked interactive local inspection. A driver/GPU-process
crash can still invalidate the whole browser renderer beyond JavaScript recovery;
long-duration visual verification remains outstanding.

Production dependency audit reported zero known vulnerabilities. Scoped review
checked graphics cleanup/lifetime, generation guards, bounded camera requests,
malformed directory IDs and preservation of fixed upstream/media trust boundaries.
Exact matching of four configured local secret values found none in changed files.
This is scoped review and dependency checking, not a repository-wide security scan.

Final local checks: API health, login page and the new dedicated overlay module
returned HTTP 200 after restarting only ASE ports 8001 and 5174. The frontend
was started with fresh dependency optimisation. Focused camera service/directory
coverage passed 33 tests at 99.56% branch-aware combined coverage, with the 90%
gate unchanged. Source-file lengths and whitespace checks passed. The earlier
traffic-focused backend modules retained their separately measured 95.23% result.
